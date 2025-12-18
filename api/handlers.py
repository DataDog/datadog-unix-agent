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
from utils.strip import mask_api_key_value
from collector import CheckLoader, WheelLoader, CoreCheckLoader

log = logging.getLogger(__name__)


class AgentStatusHandler(tornado.web.RequestHandler):
    LOADERS = [CoreCheckLoader, CheckLoader, WheelLoader]

    def initialize(self, config, started, status):
        self._config = config
        self._status = status
        self._started = started

    def get(self):
        status = {}
        check_stats = {}

        # First pass: extract consolidated check stats from collector if available
        if 'collector' in self._status:
            _, collector_info = self._status['collector'].snapshot()
            check_stats = collector_info.get('check_stats', {})

        # Second pass: process all components
        for component, stats in self._status.items():
            log.debug("adding component %s to stats", component)
            stats_snap, info_snap = stats.snapshot()
            if component == 'agent':
                info_snap = self.process_agent_info(info_snap, check_stats)
            elif component == 'collector':
                info_snap = self.process_collector_info(info_snap)

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

        status['redacted_api'] = mask_api_key_value(self._config.get('api_key'))
        status['api_status'] = validate_api_key(self._config)

        try:
            log.debug('status response to render: %s', status)
            self.write(json.dumps(status))
        except TypeError as e:
            log.error("unable to handle status request: %s", e)

    def process_agent_info(self, info, check_stats=None):
        processed = {}
        if check_stats is None:
            check_stats = {}

        # Process metrics by instance (signature)
        for signature, values in info.get('sources', {}).items():
            log.debug("processing %s, %s", signature, values)
            check_name = signature[0]
            signature_hash = signature[1]
            instance_id = "{}:{}".format(check_name, format(signature_hash, 'x'))

            # Get stats for this check instance
            stats = check_stats.get(signature_hash, {})
            config_source = stats.get('config_source', 'unknown')
            instance_index = stats.get('instance_index', 0)

            # Calculate average execution time
            exec_times_list = stats.get('execution_times', [])
            avg_exec_time = sum(exec_times_list) / len(exec_times_list) if exec_times_list else 0

            # Get total runs
            runs = stats.get('total_runs', 0)

            # Get last execution datetime
            last_exec = stats.get('last_execution')
            if last_exec:
                # Format timestamp with milliseconds (drop last 3 chars to convert microseconds to milliseconds)
                last_exec_str = last_exec.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
                last_exec_timestamp = int(last_exec.timestamp() * 1000)
                last_exec_display = "{} (ts: {})".format(last_exec_str, last_exec_timestamp)
            else:
                last_exec_display = "Never"

            processed[instance_id] = {
                'check_name': check_name,
                'signature_hash': signature_hash,
                'config_source': config_source,
                'instance_index': instance_index,
                'metrics': values,
                'service_checks': 0,
                'events': 0,
                'avg_execution_time_ms': round(avg_exec_time, 0),
                'total_runs': runs,
                'last_execution': last_exec_display
            }

        # Add service check counts from aggregator service_check_sources
        service_check_sources = info.get('service_check_sources', {})
        for signature, count in service_check_sources.items():
            check_name = signature[0]
            signature_hash = signature[1]
            instance_id = "{}:{}".format(check_name, format(signature_hash, 'x'))

            if instance_id in processed:
                processed[instance_id]['service_checks'] = count
            else:
                # Service check submitted without metrics
                stats = check_stats.get(signature_hash, {})
                config_source = stats.get('config_source', 'unknown')
                instance_index = stats.get('instance_index', 0)

                # Calculate execution stats
                exec_times_list = stats.get('execution_times', [])
                avg_exec_time = sum(exec_times_list) / len(exec_times_list) if exec_times_list else 0
                runs = stats.get('total_runs', 0)
                last_exec = stats.get('last_execution')
                if last_exec:
                    # Format timestamp with milliseconds (drop last 3 chars to convert microseconds to milliseconds)
                    last_exec_str = last_exec.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
                    last_exec_timestamp = int(last_exec.timestamp() * 1000)
                    last_exec_display = "{} (ts: {})".format(last_exec_str, last_exec_timestamp)
                else:
                    last_exec_display = "Never"

                processed[instance_id] = {
                    'check_name': check_name,
                    'signature_hash': signature_hash,
                    'config_source': config_source,
                    'instance_index': instance_index,
                    'metrics': 0,
                    'service_checks': count,
                    'events': 0,
                    'avg_execution_time_ms': round(avg_exec_time, 0),
                    'total_runs': runs,
                    'last_execution': last_exec_display
                }

        # Add event counts from aggregator event_sources
        event_sources = info.get('event_sources', {})
        for signature, count in event_sources.items():
            check_name = signature[0]
            signature_hash = signature[1]
            instance_id = "{}:{}".format(check_name, format(signature_hash, 'x'))

            if instance_id in processed:
                processed[instance_id]['events'] = count
            else:
                # Event submitted without metrics or service checks
                stats = check_stats.get(signature_hash, {})
                config_source = stats.get('config_source', 'unknown')
                instance_index = stats.get('instance_index', 0)

                # Calculate execution stats
                exec_times_list = stats.get('execution_times', [])
                avg_exec_time = sum(exec_times_list) / len(exec_times_list) if exec_times_list else 0
                runs = stats.get('total_runs', 0)
                last_exec = stats.get('last_execution')
                if last_exec:
                    # Format timestamp with milliseconds (drop last 3 chars to convert microseconds to milliseconds)
                    last_exec_str = last_exec.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
                    last_exec_timestamp = int(last_exec.timestamp() * 1000)
                    last_exec_display = "{} (ts: {})".format(last_exec_str, last_exec_timestamp)
                else:
                    last_exec_display = "Never"

                processed[instance_id] = {
                    'check_name': check_name,
                    'signature_hash': signature_hash,
                    'config_source': config_source,
                    'instance_index': instance_index,
                    'metrics': 0,
                    'service_checks': 0,
                    'events': count,
                    'avg_execution_time_ms': round(avg_exec_time, 0),
                    'total_runs': runs,
                    'last_execution': last_exec_display
                }

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
                elif loader == CoreCheckLoader.__name__:
                    processed['loader'][check][loader] = str(error['error'])

        for check, errors in runtime_errors.items():
            processed['runtime'][check] = {}
            for instance, error in errors.items():
                processed['runtime'][check][hex(instance)] = error

        return {'errors': processed}
