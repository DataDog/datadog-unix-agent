# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import sys
import types

from collector import CheckLoader, WheelLoader
from checks import AgentCheck
from collector.core_loader import CoreCheckLoader


class MockCheck(AgentCheck):
    pass


class TestCheckLoader():

    def test_load(self):
        loader = CheckLoader()
        bad_location = '/bad/location'
        location = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'fixtures'
        )
        loader.add_place(bad_location)
        loader.add_place(location)
        assert len(loader._places) == 2

        # bad check
        check, errors = loader.load('foo')
        assert check is None
        assert isinstance(errors, dict)
        assert len(errors) == 2
        assert errors.get(location) is not None
        assert errors.get(bad_location) is not None

        # good check
        check, errors = loader.load('sample_check')
        assert errors is None
        assert issubclass(check, AgentCheck)


class TestWheelLoader():

    @classmethod
    def setup_class(cls):
        # namespace module
        module_name = 'datadog_checks'
        bogus_module = types.ModuleType(module_name)
        sys.modules[module_name] = bogus_module
        # mocked check module
        check_module_name = 'datadog_checks.bogus'
        bogus_check_module = types.ModuleType(check_module_name)
        # set attribute to check module with actual AgentCheck class
        setattr(bogus_check_module, 'Bogus', MockCheck)
        bogus_module.bogus = bogus_check_module
        sys.modules[check_module_name] = bogus_check_module

    def test_load(self):
        loader = WheelLoader(namespace='datadog_checks')

        module, errors = loader._get_check_module('bogus')
        assert module is not None
        assert errors is None
        module, errors = loader._get_check_module('dontexist')
        assert module is None
        assert isinstance(errors, dict)

        check, errors = loader.load('bogus')
        assert errors is None
        assert issubclass(check, AgentCheck)


class TestCoreCheckLoader(object):

    def setup_method(self):
        # snapshot sys.modules so each test can mutate it safely
        self._orig_sys_modules = dict(sys.modules)

    def teardown_method(self):
        # restore original module state
        sys.modules.clear()
        sys.modules.update(self._orig_sys_modules)

    # -----------------------
    # Helpers
    # -----------------------
    def _install_fake_corecheck_cpu(self, tmpdir, monkeypatch):
        import sys
        import types

        #
        # 1. Create real filesystem structure for loader scanning
        #
        cpu_dir = (
            tmpdir.mkdir("checks")
            .mkdir("corechecks")
            .mkdir("system")
            .mkdir("cpu")
        )
        cpu_file = cpu_dir.join("cpu.py")
        cpu_file.write(
            "from checks import AgentCheck\n"
            "class CpuV2(AgentCheck): pass\n"
        )

        #
        # 2. Fake sys.modules hierarchy with correct __path__
        #
        from checks import AgentCheck as RealAgentCheck

        # checks
        checks_pkg = types.ModuleType("checks")
        checks_pkg.__path__ = [str(tmpdir / "checks")]
        checks_pkg.AgentCheck = RealAgentCheck
        sys.modules["checks"] = checks_pkg

        # checks.corechecks
        cc_pkg = types.ModuleType("checks.corechecks")
        cc_pkg.__path__ = [str(tmpdir / "checks" / "corechecks")]
        sys.modules["checks.corechecks"] = cc_pkg

        # checks.corechecks.system
        sys_pkg = types.ModuleType("checks.corechecks.system")
        sys_pkg.__path__ = [str(tmpdir / "checks" / "corechecks" / "system")]
        sys.modules["checks.corechecks.system"] = sys_pkg

        # checks.corechecks.system.cpu
        cpu_pkg = types.ModuleType("checks.corechecks.system.cpu")
        cpu_pkg.__path__ = [
            str(tmpdir / "checks" / "corechecks" / "system" / "cpu")]
        sys.modules["checks.corechecks.system.cpu"] = cpu_pkg

        # remove stale cached module if it exists
        sys.modules.pop("checks.corechecks.system.cpu.cpu", None)

        #
        # 3. Allow importlib to import cpu.py
        #
        monkeypatch.syspath_prepend(str(tmpdir))

    def _install_fake_core_root_without_check(self):
        """
        Install a fake core root with no check categories or checks.
        Used to simulate missing checks.
        """
        import sys
        import types
        from checks import AgentCheck as RealAgentCheck

        checks_pkg = types.ModuleType("checks")
        checks_pkg.AgentCheck = RealAgentCheck
        sys.modules["checks"] = checks_pkg

        cc_pkg = types.ModuleType("checks.corechecks")
        sys.modules["checks.corechecks"] = cc_pkg

        sys_pkg = types.ModuleType("checks.corechecks.system")
        sys.modules["checks.corechecks.system"] = sys_pkg

    def _install_fake_corecheck_badcheck(self, tmpdir, monkeypatch):
        import sys
        import types

        #
        # 1. Create real directory structure
        #
        bad_dir = (
            tmpdir.mkdir("checks")
            .mkdir("corechecks")
            .mkdir("system")
            .mkdir("badcheck")
        )
        bad_file = bad_dir.join("badcheck.py")
        # no AgentCheck subclass
        bad_file.write("class NotACheck(object): pass\n")

        #
        # 2. Fake package tree with proper __path__
        #
        from checks import AgentCheck as RealAgentCheck

        checks_pkg = types.ModuleType("checks")
        checks_pkg.__path__ = [str(tmpdir / "checks")]
        checks_pkg.AgentCheck = RealAgentCheck
        sys.modules["checks"] = checks_pkg

        cc_pkg = types.ModuleType("checks.corechecks")
        cc_pkg.__path__ = [str(tmpdir / "checks" / "corechecks")]
        sys.modules["checks.corechecks"] = cc_pkg

        sys_pkg = types.ModuleType("checks.corechecks.system")
        sys_pkg.__path__ = [str(tmpdir / "checks" / "corechecks" / "system")]
        sys.modules["checks.corechecks.system"] = sys_pkg

        bad_pkg = types.ModuleType("checks.corechecks.system.badcheck")
        bad_pkg.__path__ = [
            str(tmpdir / "checks" / "corechecks" / "system" / "badcheck")]
        sys.modules["checks.corechecks.system.badcheck"] = bad_pkg

        # clear stale module
        sys.modules.pop("checks.corechecks.system.badcheck.badcheck", None)

        #
        # 3. Allow importlib to find badcheck.py
        #
        monkeypatch.syspath_prepend(str(tmpdir))

    # -----------------------
    # Tests
    # -----------------------
    def test_core_loader_loads_cpu(self, tmpdir, monkeypatch):
        self._install_fake_corecheck_cpu(tmpdir, monkeypatch)

        loader = CoreCheckLoader()
        check_class, errors = loader.load("cpu")

        assert errors is None
        assert check_class is not None
        assert check_class.__name__ == "CpuV2"
        assert issubclass(check_class, AgentCheck)

    def test_core_loader_missing_check_returns_none(self):
        self._install_fake_core_root_without_check()

        loader = CoreCheckLoader()
        check_class, errors = loader.load("does_not_exist")

        assert check_class is None
        assert errors is None

    def test_core_loader_badcheck_without_agentcheck(self, tmpdir, monkeypatch):
        self._install_fake_corecheck_badcheck(tmpdir, monkeypatch)

        loader = CoreCheckLoader()
        check_class, errors = loader.load("badcheck")

        assert check_class is None
        assert isinstance(errors, dict)
        assert "error" in errors
        assert "traceback" in errors
