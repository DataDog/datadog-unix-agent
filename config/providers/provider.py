# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


class ConfigProvider(object):

    def collect(self):
        '''Collect available configurations. Abstract.'''
        raise NotImplementedError

    def validate_config(self, config):
        '''Validates right config format'''
        if not config or not isinstance(config, dict):
            return False

        return 'instances' in config
