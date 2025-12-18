# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import yaml
import logging
from collections import defaultdict

from .provider import ConfigProvider


log = logging.getLogger(__name__)


class FileConfigProvider(ConfigProvider):
    VALID_EXTENSIONS = [
        '.yaml',
    ]
    VALID_DEFAULT_EXTENSIONS = [
        '.yaml.default',
    ]

    def __init__(self):
        self._places = set()
        super(FileConfigProvider, self).__init__()

    def add_place(self, place):
        if not os.path.isdir(place):
            return False

        self._places.update([os.path.realpath(place)])
        return True

    def collect(self):
        configs = defaultdict(list)
        defaults = defaultdict(list)

        config_yamls = self._get_config_yamls()
        for config_path, config_file, is_default in config_yamls:
            yaml_path = os.path.join(config_path, config_file)

            # First, validate directory structure before parsing YAML
            place = None
            for _place in self._places:
                if os.path.realpath(config_path).startswith(_place):
                    place = _place
                    break

            check = self._get_check_name_from_path(place, yaml_path)
            if check is None:
                # Invalid config path, skip it
                continue

            # Now parse and validate YAML
            with open(yaml_path, 'r') as stream:
                try:
                    yaml_config = yaml.safe_load(stream)
                except yaml.YAMLError as e:
                    log.warn('unable to load YAML for %s: %s', yaml_path, e)
                    continue

                if not self.validate_config(yaml_config):
                    log.warn('bad configuration YAML in %s', yaml_path)
                    continue

            place = None
            for _place in self._places:
                if os.path.realpath(config_path).startswith(_place):
                    place = _place
                    break

            check = self._get_check_name_from_path(place, yaml_path)
            flat_configs = self._flatten_config(yaml_config, yaml_path)
            if is_default:
                defaults[check].extend(flat_configs)
            else:
                configs[check].extend(flat_configs)

        # update configs with missing defaults
        for check in defaults:
            if check not in configs:
                configs[check] = defaults[check]

        return configs

    def _get_config_yamls(self):
        configs = []
        for place in self._places:
            for dirpath, dirs, files in os.walk(place):
                for cfile in files:
                    valid_config = False
                    default_config = False
                    for ext in self.VALID_EXTENSIONS:
                        if cfile.endswith(ext):
                            valid_config = True
                            break
                    for ext in self.VALID_DEFAULT_EXTENSIONS:
                        if cfile.endswith(ext):
                            valid_config = True
                            default_config = True
                            break

                    if not valid_config:
                        continue

                    configs.append((dirpath, cfile, default_config))

        return configs

    def _get_check_name_from_path(self, base, path):
        relative = os.path.relpath(path, base)
        if not relative:
            return None

        subdir, config = os.path.split(relative)
        if not subdir:
            return os.path.splitext(os.path.basename(path))[0]

        if not subdir.endswith('.d'):
            # Log just the directory path, not the full file path
            invalid_dir = os.path.dirname(path)
            log.warning("Skipped config directory (expected *.d): %s", invalid_dir)
            return None

        return subdir.split('.')[0]

    def _flatten_config(self, config, config_path=None):
        if not isinstance(config, dict):
            raise ValueError("expected a dictionary")

        configs = []
        init_config = config.get('init_config', {})
        instances = config.get('instances', {}) or []
        for instance_index, instance in enumerate(instances):
            config_dict = {
                'init_config': init_config,
                'instances': [instance]
            }
            # Add metadata for tracking config source and instance index
            if config_path:
                config_dict['_config_source'] = config_path
                config_dict['_instance_index'] = instance_index
            configs.append(config_dict)

        return configs
