# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from datetime import datetime
import json
import logging
import os
import sys

import tornado

from utils.hostname import get_hostname, HostnameException
from utils.api import validate_api_key
from collector import CheckLoader, WheelLoader

log = logging.getLogger(__name__)


class APIStatusHandler(tornado.web.RequestHandler):
    LOADERS = [CheckLoader, WheelLoader]

    def initialize(self, config, collector, started, aggregator_stats):
        self._config = config
        self._collector = collector
        self._aggregator_stats = aggregator_stats
        self._started = started

    def get(self):
        stats = self._aggregator_stats.get_aggregator_stats()

        check_stats = stats.pop('stats')
        stats['checks'] = {}
        for signature, values in check_stats.items():
            check = signature[0]
            if check in stats['checks']:
                stats['checks'][check]['merics'] += values
            else:
                stats['checks'][check] = {'metrics': values}

        stats['errors'] = {}
        for check, errors in self._collector.collector_status().items():
            if check in stats['checks']:  # check eventually loaded
                continue

            stats['errors'][check] = {}
            for loader, error in errors.items():
                if loader == CheckLoader.__name__:
                    for place, err in error.items():
                        stats['errors'][check][loader] = '{path}: {err}'.format(path=place, err=err['error'])
                    pass
                elif loader == WheelLoader.__name__:
                    stats['errors'][check][loader] = str(error['error'])

        now = datetime.utcnow()
        stats['uptime'] = (now - self._started).total_seconds()
        stats['utc_time'] = now.strftime("%a, %d %b %Y %H:%M:%S.%f %Z")

        stats['pid'] = os.getpid()
        stats['python_version'] = "{major}.{minor}.{bugfix}".format(
            major=sys.version_info[0],
            minor=sys.version_info[1],
            bugfix=sys.version_info[2]
        )

        stats['agent_log_path'] = self._config.get('logging', {}).get('agent_log_file')
        stats['agent_config_path'] = self._config.get_loaded_config()
        stats['log_level'] = self._config.get('log_level', 'INFO').upper()

        try:
            stats['hostname'] = get_hostname()
            stats['hostname_native'] = get_hostname(config_override=False)
        except HostnameException:
            stats['hostname'] = '' if 'hostname' not in stats else stats['hostname']
            stats['hostname_native'] = ''

        stats['redacted_api'] = '*'*20 + self._config.get('api_key')[-5:]
        stats['api_status'] = validate_api_key(self._config)

        try:
            self.write(json.dumps(stats))
        except TypeError as e:
            log.error("unable to handle status request: {}".format(e))
