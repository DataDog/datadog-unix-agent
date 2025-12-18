# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

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

        file_two = '/etc/datadog-agent/conf.d/foo.d/conf.yaml'
        check = provider._get_check_name_from_path(place, file_two)
        assert check == "foo"

        # Invalid directory structure should return None instead of raising exception
        file_invalid = '/etc/datadog-agent/conf.d/foo/conf.yaml'
        check = provider._get_check_name_from_path(place, file_invalid)
        assert check is None

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

    def test_invalid_directory_structure(self, tmpdir):
        """Test that invalid config directories (not ending in .d) are skipped gracefully."""
        provider = FileConfigProvider()

        # Create valid config directory (ends with .d)
        valid_dir = tmpdir.mkdir("conf.d").mkdir("valid_check.d")
        valid_config = valid_dir.join("conf.yaml")
        valid_config.write("""init_config:

instances:
  - {}
""")

        # Create invalid config directory (doesn't end with .d)
        conf_d = tmpdir.join("conf.d")
        invalid_dir = conf_d.mkdir("invalid_check")
        invalid_config = invalid_dir.join("conf.yaml")
        invalid_config.write("""init_config:

instances:
  - {}
""")

        # Add the conf.d directory
        provider.add_place(str(conf_d))

        # Collect configs - should not raise exception
        configs = provider.collect()

        # Should have the valid check
        assert 'valid_check' in configs
        assert len(configs['valid_check']) == 1

        # Should NOT have the invalid check (it was skipped)
        assert 'invalid_check' not in configs
