# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import yaml
import logging

from deepmerge import always_merger

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
        self._places = set([])
        super(FileConfigProvider, self).__init__()

    def add_place(self, place):
        if not os.path.isdir(place):
            return False

        self._places.update(place)
        return True

    def collect(self):
        configs = {}
        defaults = {}

        config_yamls = self._get_config_yamls()
        for place, config_file, is_default in config_yamls:
            yaml_path = os.path.join(place, config_file)
            with open(yaml_path, 'r') as stream:
                try:
                    yaml_config = yaml.load(stream)
                except yaml.YAMLError as e:
                    log.warn('unable to load YAML for %s: %s', yaml_path, e)
                    continue

                if not self.validate_config(yaml_config):
                    log.warn('bad configuration YAML in %s', yaml_path)
                    continue

            check = self._get_check_from_path(yaml_path, place)
            if is_default:
                if check in defaults:
                    defaults[check] = self._merge_configs(defaults[check],
                                                          yaml_config)
                else:
                    defaults[check] = yaml_config
            else:
                if check in configs:
                    configs[check] = self._merge_configs(configs[check],
                                                         yaml_config)
                else:
                    configs[check] = yaml_config

        # update configs with missing defaults
        for check in defaults:
            if check not in configs:
                configs[check] = defaults[check]

        return configs

    def _get_config_yamls(self):
        configs = []
        for place in self._places:
            dirpath, dirs, files = os.walk(place)
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

                configs.append((place, cfile, default_config))

    def _get_check_from_path(self, base, path):
        relative = os.path.relpath(path, base)
        if not relative:
            return None

        subdir, config = os.path.split(relative)
        if not subdir:
            return os.path.splitext(os.path.basename(path))[0]

        return os.path.split(subdir)[0]

    def _merge_configs(orig, new):
        return always_merger(orig, new)
