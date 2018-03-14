# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

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
            with open(yaml_path, 'r') as stream:
                try:
                    yaml_config = yaml.load(stream)
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
            flat_configs = self._flatten_config(yaml_config)
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

        return subdir

    def _flatten_config(self, config):
        if not isinstance(config, dict):
            raise ValueError("expected a dictionary")

        configs = []
        init_config = config.get('init_config', {})
        for instance in config.get('instances', {}):
            configs.append({'init_config': init_config,
                            'instances': [instance]})

        return configs
