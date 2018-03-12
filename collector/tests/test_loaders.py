# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import sys
import types

from collector import CheckLoader, WheelLoader
from checks import AgentCheck


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
