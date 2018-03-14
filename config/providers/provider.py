# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.


class ConfigProvider(object):

    def collect(self):
        '''Collect available configurations. Abstract.'''
        raise NotImplementedError

    def validate_config(self, config):
        '''Validates right config format'''
        if not config or not isinstance(config, dict):
            return False

        return 'instances' in config
