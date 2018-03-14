# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import pytest

from config.providers import FileConfigProvider


class TestFileProvider():

    def test_config_flatten(self):
        config = {
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

        with pytest.raises(ValueError):
            provider._flatten_config(None)

        with pytest.raises(ValueError):
            provider._flatten_config([])

        flat = provider._flatten_config(config)
        assert len(flat) == 2
        for cfg in flat:
            assert 'init_config' in cfg
            assert 'instances' in cfg
            assert len(cfg['instances']) == 1

    def test_checkname_extract(self):
        provider = FileConfigProvider()

        place = "/etc/datadog-agent/conf.d"
        file_one = '/etc/datadog-agent/conf.d/foo.yaml'

        check = provider._get_check_name_from_path(place, file_one)
        assert check == "foo"

        file_two = '/etc/datadog-agent/conf.d/foo/conf.yaml'
        check = provider._get_check_name_from_path(place, file_two)
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
        assert len(configs['sample_check']) == 2
