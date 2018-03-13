# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

from config.providers import FileConfigProvider


class TestFileProvider():

    def test_config_merge(self):
        config_a = {
            'init_config': None,
            'instances': [
                {
                    'name': 'foo',
                    'uri': 'localhost:5555'
                }
            ]
        }
        config_b = {
            'init_config': {
                'param': 1203192
            },
            'instances': [
                {
                    'name': 'bar',
                    'uri': 'localhost:4444'
                },
                {
                    'name': 'haz',
                    'uri': 'localhost:3333'
                },
            ]
        }
        provider = FileConfigProvider()

        merged = provider._merge_configs(config_a, config_b)
        assert merged is not None
        assert len(merged['instances']) == 3
        assert merged['init_config'] is not None
        assert merged['init_config']['param'] == 1203192

        config_c = {
            'init_config': {
                'args': 'someargument'
            },
            'instances': []
        }

        merged = provider._merge_configs(merged, config_c)
        assert 'param' in merged['init_config']
        assert 'args' in merged['init_config']
        assert merged['init_config']['args'] == 'someargument'

    def test_checkname_extract(self):
        provider = FileConfigProvider()

        place = "/etc/datadog-agent/conf.d"
        file_one = '/etc/datadog-agent/conf.d/foo.yaml'

        check = provider._get_check_from_path(place, file_one)
        assert check == "foo"

        file_two = '/etc/datadog-agent/conf.d/foo/conf.yaml'
        check = provider._get_check_from_path(place, file_two)
        assert check == "foo"

    def test_provider(self):
        provider = FileConfigProvider()

        config_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'fixtures',
            'conf.d',
        )

        provider.add_place(config_path)
        assert len(provider._places) == 1

        configs = provider.collect()
        assert len(configs) > 0
        assert 'sample_check' in configs
        assert len(configs['sample_check']['instances']) == 2
