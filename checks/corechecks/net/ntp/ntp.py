# checks/corechecks/net/ntp/ntp.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.

import random
import socket
import ntplib

from checks import AgentCheck
from .__about__ import __version__


DEFAULT_OFFSET_THRESHOLD = 60
DEFAULT_HOST = '{}.datadog.pool.ntp.org'.format(random.randint(0, 3))
DEFAULT_VERSION = 3
DEFAULT_TIMEOUT = 1.0
DEFAULT_PORT = 'ntp'
DEFAULT_PORT_NUM = 123


class NTPCheck(AgentCheck):

    __version__ = __version__
    DEFAULT_MIN_COLLECTION_INTERVAL = 15  # seconds

    def _get_service_port(self, instance):
        """
        Get the NTP server port, falling back to numeric 123 if service lookup fails.
        """
        host = instance.get('host', DEFAULT_HOST)
        port = instance.get('port', DEFAULT_PORT)

        try:
            socket.getaddrinfo(host, port)
        except socket.gaierror:
            port = DEFAULT_PORT_NUM

        return port

    def check(self, instance):
        service_check_msg = None
        custom_tags = instance.get('tags', [])

        offset_threshold = instance.get(
            'offset_threshold', DEFAULT_OFFSET_THRESHOLD
        )
        try:
            offset_threshold = int(offset_threshold)
        except (TypeError, ValueError):
            raise Exception(
                "Must specify an integer value for offset_threshold. "
                "Configured value is {}".format(offset_threshold)
            )

        req_args = {
            'host': instance.get('host', DEFAULT_HOST),
            'port': self._get_service_port(instance),
            'version': int(instance.get('version', DEFAULT_VERSION)),
            'timeout': float(instance.get('timeout', DEFAULT_TIMEOUT)),
        }

        self.log.debug("Using NTP host: {}".format(req_args['host']))

        ntp_ts = None

        try:
            ntp_stats = ntplib.NTPClient().request(**req_args)
        except ntplib.NTPException:
            self.log.debug("Could not connect to NTP Server {}".format(req_args['host']))
            status = AgentCheck.UNKNOWN
        else:
            ntp_offset = ntp_stats.offset
            ntp_ts = ntp_stats.recv_time

            self.gauge(
                'ntp.offset',
                ntp_offset,
                timestamp=ntp_ts,
                tags=custom_tags,
            )

            if abs(ntp_offset) > offset_threshold:
                status = AgentCheck.CRITICAL
                service_check_msg = (
                    "Offset {} secs higher than offset threshold ({} secs)"
                    .format(ntp_offset, offset_threshold)
                )
            else:
                status = AgentCheck.OK

        # Report service check
        self.service_check(
            'ntp.in_sync',
            status,
            timestamp=ntp_ts,
            message=service_check_msg,
            tags=custom_tags,
        )
