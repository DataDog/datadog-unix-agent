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


class AgentStatusHandler(tornado.web.RequestHandler):
    LOADERS = [CheckLoader, WheelLoader]

    def initialize(self, config, started, status):
        self._config = config
        self._status = status
        self._started = started

    def get(self):
        status = {}

        for component, stats in self._status.items():
            log.debug("adding component %s to stats", component)
            stats_snap, info_snap = stats.snapshot()
            if component == 'agent':
                info_snap = self.process_agent_info(info_snap)
            elif component == 'collector':
                info_snap = self.process_collector_info(info_snap)

            log.debug("processed %s info: %s", component, info_snap)

            status[component] = {
                'stats': stats_snap,
                'info': info_snap,
            }

        now = datetime.utcnow()
        status['uptime'] = (now - self._started).total_seconds()
        status['utc_time'] = now.strftime("%a, %d %b %Y %H:%M:%S.%f %Z")

        status['pid'] = os.getpid()
        status['python_version'] = "{major}.{minor}.{bugfix}".format(
            major=sys.version_info[0],
            minor=sys.version_info[1],
            bugfix=sys.version_info[2]
        )

        status['agent_log_path'] = self._config.get('logging', {}).get('agent_log_file')
        status['agent_config_path'] = self._config.get_loaded_config()
        status['log_level'] = self._config.get('log_level', 'INFO').upper()

        try:
            status['hostname'] = get_hostname()
            status['hostname_native'] = get_hostname(config_override=False)
        except HostnameException:
            status['hostname'] = '' if 'hostname' not in status else status['hostname']
            status['hostname_native'] = ''

        status['redacted_api'] = '*'*20 + self._config.get('api_key')[-5:]
        status['api_status'] = validate_api_key(self._config)

        try:
            log.debug('status response to render: %s', status)
            self.write(json.dumps(status))
        except TypeError as e:
            log.error("unable to handle status request: {}".format(e))

    def process_agent_info(self, info):
        processed = {}

        for signature, values in info.get('sources', {}).items():
            log.debug("processing %s, %s", signature, values)
            check = signature[0]
            if check in processed:
                processed['sources'][check]['merics'] += values
            else:
                processed[check] = {'metrics': values}

        return {'checks': processed}

    def process_collector_info(self, info):
        processed = {
            'loader': {},
            'runtime': {},
        }

        check_classes = info.get('check_classes', {})
        loader_errors = info.get('loader_errors', {})
        runtime_errors = info.get('runtime_errors', {})

        for check, errors in loader_errors.items():
            if check in check_classes:  # check eventually loaded
                continue

            processed['loader'][check] = {}
            for loader, error in errors.items():
                if loader == CheckLoader.__name__:
                    for place, err in error.items():
                        processed['loader'][check][loader] = '{path}: {err}'.format(path=place, err=err['error'])
                elif loader == WheelLoader.__name__:
                    processed['loader'][check][loader] = str(error['error'])

        for check, errors in runtime_errors.items():
            processed['runtime'][check] = {}
            for instance, error in errors.items():
                processed['runtime'][check][hex(instance)] = error

        return {'errors': processed}
