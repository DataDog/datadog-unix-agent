# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging
from threading import Thread

from aggregator import MetricsBucketAggregator
from aggregator.formatters import get_formatter
from forwarder import Forwarder
from serialize import Serializer
from utils.hostname import get_hostname
from utils.network import get_proxy

from .constants import (  # pylint: disable=no-name-in-module
    DOGSTATSD_FLUSH_INTERVAL,
    DOGSTATSD_AGGREGATOR_BUCKET_SIZE,
)
from . import (
    Server,
    Reporter,
)

log = logging.getLogger('dogstatsd')


def init_dogstatsd(config, forwarder=None):
    api_key = config['api_key']
    recent_point_threshold = config.get('recent_point_threshold', None)
    server_host = config['dogstatsd']['bind_host']
    dd_url = config['dd_url']
    port = config['dogstatsd']['port']
    forward_to_host = config['dogstatsd'].get('forward_host')
    forward_to_port = config['dogstatsd'].get('forward_port')
    non_local_traffic = config['dogstatsd'].get('non_local_traffic')
    so_rcvbuf = config['dogstatsd'].get('so_rcvbuf')
    utf8_decoding = config['dogstatsd'].get('utf8_decoding')

    interval = DOGSTATSD_FLUSH_INTERVAL
    aggregator_interval = DOGSTATSD_AGGREGATOR_BUCKET_SIZE

    hostname = get_hostname()

    # get proxy settings
    proxies = get_proxy()

    if not forwarder:
        forwarder = Forwarder(
            api_key,
            dd_url,
            proxies=proxies,
        )

    aggregator = MetricsBucketAggregator(
        hostname,
        aggregator_interval,
        recent_point_threshold=recent_point_threshold,
        formatter=get_formatter(config),
        histogram_aggregates=config.get('histogram_aggregates'),
        histogram_percentiles=config.get('histogram_percentiles'),
        utf8_decoding=utf8_decoding
    )
    # serializer
    serializer = Serializer(
        aggregator,
        forwarder,
    )

    reporter = Reporter(interval, aggregator, serializer, api_key,
                        use_watchdog=False, hostname=hostname)

    # NOTICE: when `non_local_traffic` is passed we need to bind to any interface on the box. The forwarder uses
    # Tornado which takes care of sockets creation (more than one socket can be used at once depending on the
    # network settings), so it's enough to just pass an empty string '' to the library.
    # In Dogstatsd we use a single, fullstack socket, so passing '' as the address doesn't work and we default to
    # '0.0.0.0'. If someone needs to bind Dogstatsd to the IPv6 '::', they need to turn off `non_local_traffic` and
    # use the '::' meta address as `bind_host`.
    if non_local_traffic:
        server_host = '0.0.0.0'

    server = Server(aggregator, server_host, port, forward_to_host=forward_to_host,
                    forward_to_port=forward_to_port, so_rcvbuf=so_rcvbuf)

    return reporter, server, forwarder


class DogstatsdRunner(Thread):
    def __init__(self, server):
        super(DogstatsdRunner, self).__init__()
        self._server = server
        self._error = None

    def stop(self):
        log.info('Stopping Dogstatsd Runner...')
        self._server.stop()

    def run(self):
        log.info('Starting Dogstatsd Runner...')

        try:
            self._server.start()
        except OSError as e:
            self._error = e

    def raise_for_status(self):
        if self._error:
            raise self._error
