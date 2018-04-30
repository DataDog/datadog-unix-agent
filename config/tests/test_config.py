# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import copy
import os
import tempfile
import pytest

from config import Config
from config.providers import ConfigProvider, FileConfigProvider


@pytest.fixture
def conf():
    return Config()


class DummyConfigProvider(ConfigProvider):

    def __init__(self):
        self.foo = {
            'init_config': {
                'someopt': 1
            },
            'instances': [
                {
                    'url': 'https://localhost:5555',
                    'user': 'datadog',
                    'password': 'ub3rSecuR3'
                },
                {
                    'url': 'https://remote.host:4444',
                    'user': 'datapoodle',
                    'password': 'insecurrr'
                },
            ]
        }
        self.bar = {
            'init_config': {},
            'instances': [
                {
                    'sock': '/var/run/app/app.sock',
                },
            ]
        }
        super(DummyConfigProvider, self).__init__()

    def collect(self):
        ''' Collect available configurations.'''
        bar_copy = copy.deepcopy(self.bar)
        bar_copy['init_config']['baropts'] = '-x -y -z'
        return {
            'foo': [self.foo],
            'bar': [self.bar, bar_copy],
        }


class TestConfig():
    def test_init(self, conf):
        assert conf.search_paths == set()
        assert conf.conf_name == "datadog.yaml"
        assert conf.env_prefix == "DD_"
        assert conf.env_bindings == set()
        assert conf.data == {}
        assert conf.defaults == {}

    def test_empty_conf(self, conf):
        assert conf.get("test") is None
        assert conf.load() is None

    def test_default(self, conf):
        conf.set_default("test", 21)
        conf.load()
        assert conf.get("test") == 21

    def test_set_and_reset(self, conf):
        assert conf.get("test") is None
        conf.set("test", 21)
        assert conf.get("test") == 21
        conf.reset("test")
        assert conf.get("test") is None
        conf['test'] = 42
        assert conf['test'] == 42
        del conf['test']
        with pytest.raises(KeyError):
            conf['test']

    def test_load(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\nlist: [1, 2, 3]")

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)
        conf.load()

        assert conf.get("test") == 123
        assert conf.get("list") == [1, 2, 3]

        os.close(fd)
        os.remove(tmpfile)

    def test_get(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\ntest2: true\nlist: [1, 2, 3]")

        os.environ["DD_test2"] = "env_val"
        os.environ["DD_test3"] = "env_val2"

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)

        conf.set_default("test1", "default")
        conf.set_default("test2", "default")
        conf.bind_env("test2")
        conf.bind_env_and_set_default("test3", False)
        conf.load()

        assert conf.get("test1") == "default"
        assert conf.get("test2") == "env_val"
        assert conf.get("test3") == "env_val2"
        assert conf.get("list") == [1, 2, 3]

        assert conf["test1"] == "default"
        assert conf["test2"] == "env_val"
        assert conf["test3"] == "env_val2"
        assert conf["list"] == [1, 2, 3]

        os.close(fd)
        os.remove(tmpfile)

    def test_validate_aggregates_sane(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_aggregates: [min, max, median]")

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)
        conf.load()

        assert isinstance(conf.get("histogram_aggregates"), list)
        assert len(conf.get("histogram_aggregates")) == 3
        for t in ['min', 'max', 'median']:
            assert t in conf.get("histogram_aggregates")

        os.close(fd)
        os.remove(tmpfile)

    def test_validate_aggregates_sanitized(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_aggregates: [min, max, median, foo]")

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)
        conf.load()

        assert isinstance(conf.get("histogram_aggregates"), list)
        assert len(conf.get("histogram_aggregates")) == 3
        for t in ['min', 'max', 'median']:
            assert t in conf.get("histogram_aggregates")

        os.close(fd)
        os.remove(tmpfile)

    def test_validate_percentiles(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_percentiles: [0.98, 0.23, 0.1321]")

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)

        conf.load()

        assert len(conf.get("histogram_percentiles")) == 3
        for v in [0.98, 0.23, 0.13]:
            assert v in conf.get("histogram_percentiles")

        os.close(fd)
        os.remove(tmpfile)

    def test_validate_percentiles_hich_precision(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_percentiles: [0.999, 0.23, 0.1321]")

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)

        conf.load()

        assert len(conf.get("histogram_percentiles")) == 3
        for v in [0.99, 0.23, 0.13]:
            assert v in conf.get("histogram_percentiles")

        os.close(fd)
        os.remove(tmpfile)

    def test_validate_percentiles_badval(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_percentiles: [0.98, foo]")

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)

        conf.load()

        assert len(conf.get("histogram_percentiles")) == 1
        assert conf.get("histogram_percentiles") == [0.98]

        os.close(fd)
        os.remove(tmpfile)

    def test_validate_percentiles_bounds(self, conf):
        fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
        os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_percentiles: [1, 0]")

        conf.add_search_path(os.path.dirname(tmpfile))
        conf.conf_name = os.path.basename(tmpfile)

        conf.load()

        assert len(conf.get("histogram_percentiles")) == 0

        os.close(fd)
        os.remove(tmpfile)

    def test_config_providers(self, conf):
        provider = DummyConfigProvider()
        file_provider = FileConfigProvider()

        config_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'fixtures',
            'conf.d',
        )
        file_provider.add_place(config_path)

        conf.add_provider('dummy_source', provider)
        conf.add_provider('file', file_provider)

        conf.collect_check_configs()
        assert len(conf._check_configs) > 0

        configs = conf.get_check_configs()
        assert 'dummy_source' in configs
        assert 'foo' in configs['dummy_source']
        assert 'bar' in configs['dummy_source']
        assert len(configs['dummy_source']['foo']) == 1
        assert len(configs['dummy_source']['bar']) == 2
        for check in ['foo', 'bar']:
            for config in configs['dummy_source'][check]:
                assert 'init_config' in config
                assert 'instances' in config
                assert isinstance(config['instances'], list)

        assert 'file' in configs
        assert 'sample_check' in configs['file']
        assert len(configs['file']['sample_check']) == 2
        for config in configs['file']['sample_check']:
            assert 'init_config' in config
            assert 'instances' in config
            assert isinstance(config['instances'], list)

    def test_env_namespaces(self):
        config = Config()

        test_env_var = "DD_FOO_BAR_HaZ"
        namespaces = config.env_var_namespaces(test_env_var)
        assert len(namespaces) == 5

        for prefix, suffix in namespaces:
            if prefix and suffix:
                assert "{}_{}".format(prefix, suffix) == test_env_var
            elif suffix:
                assert suffix == test_env_var
            else:
                assert prefix == test_env_var

    def test_env_override(self):
        config = Config()

        config.data = {
            'logging': {
                'agent_log_file': 'foo',
                'dogstatsd_log_file': 'bar',
            },
            'comics':
            {
                'marvel': {
                    'hulk': 'unknown'
                }
            }
        }
        config.defaults = {
            'comics':
            {
                'dc': {
                    'flash': 'unknown'
                }
            }
        }

        os.environ['DD_LOGGING_AGENT_LOG_FILE'] = 'qux'
        os.environ['DD_LOGGING_DOGSTATSD_LOG_FILE'] = 'lulz'
        os.environ['DD_COMICS_MARVEL_HULK'] = 'bruce banner'
        os.environ['DD_COMICS_DC_FLASH'] = 'barry allen'

        override = config.env_override('DD_LOGGING_AGENT_LOG_FILE', 'logging_agent_log_file')
        override &= config.env_override('DD_LOGGING_DOGSTATSD_LOG_FILE', 'logging_dogstatsd_log_file')
        override &= config.env_override('DD_COMICS_MARVEL_HULK', 'comics_marvel_hulk')
        override &= config.env_override('DD_COMICS_DC_FLASH', 'comics_dc_flash')
        assert override is True
        assert config.data['logging']['agent_log_file'] == 'qux'
        assert config.data['logging']['dogstatsd_log_file'] == 'lulz'
        assert config.data['comics']['marvel']['hulk'] == 'bruce banner'
        assert config.data['comics']['dc']['flash'] == 'barry allen'
