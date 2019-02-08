#!/opt/datadog-agent/embedded/bin/python

# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging
import optparse
import signal
import sys

from aggregator import MetricsBucketAggregator
from aggregator.formatters import get_formatter
from config import config
from serialize import Serializer
from forwarder import Forwarder
from utils.hostname import get_hostname
from utils.logs import initialize_logging
from utils.network import get_proxy
from utils.signals import SignalHandler

from dogstatsd import (
    Server,
    Reporter,
)
from dogstatsd.constants import (  # pylint: disable=no-name-in-module
    DOGSTATSD_FLUSH_INTERVAL,
    DOGSTATSD_AGGREGATOR_BUCKET_SIZE,
)

log = logging.getLogger('dogstatsd')


def init_config():
    config.add_search_path("/etc/datadog-unix-agent")
    config.add_search_path(".")
    try:
        config.load()
    finally:
        initialize_logging('dogstatsd')


def init_dogstatsd(config):
    api_key = config['api_key']
    recent_point_threshold = config.get('recent_point_threshold', None)
    server_host = config['bind_host']
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

    forwarder = Forwarder(
        api_key,
        dd_url,
        proxies=proxies,
    )
    forwarder.start()

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


def main(config_path=None):
    """ The main entry point for the unix version of dogstatsd. """
    COMMANDS_START_DOGSTATSD = [
        'start',
        'restart',
    ]

    parser = optparse.OptionParser("%prog [start|stop|restart|status]")
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                      dest="use_forwarder", default=False)
    opts, args = parser.parse_args()

    try:
        init_config()
    except Exception as e:
        logging.error("Problem initializing configuration: %s", e)
        return 1

    if not args or args[0] in COMMANDS_START_DOGSTATSD:
        reporter, server, forwarder = init_dogstatsd(config)

    # If no args were passed in, run the server in the foreground.
    command = 'start' if not args else args[0]

    if command == 'start'or command == 'restart':

        handler = SignalHandler()
        # components
        handler.register('forwarder', forwarder)
        handler.register('server', server)
        handler.register('reporter', reporter)
        # signals
        handler.handle(signal.SIGTERM)
        handler.handle(signal.SIGINT)

        # start signal handler
        handler.start()

        # start components
        reporter.start()
        server.start()

        reporter.join()
        logging.info("Dogstatsd reporter done...")

        handler.stop()
        handler.join()

        logging.info("Thank you for shopping at DataDog! Come back soon!")
    else:
        sys.stderr.write("Unknown command: %s\n\n" % command)
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
