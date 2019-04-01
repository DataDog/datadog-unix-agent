#!/opt/datadog-agent/embedded/bin/python

# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging
import optparse
import signal
import os
import sys

from aggregator import MetricsBucketAggregator
from aggregator.formatters import get_formatter
from config import config
from config.default import DEFAULT_PATH
from serialize import Serializer
from forwarder import Forwarder
from utils.daemon import Daemon
from utils.hostname import get_hostname
from utils.logs import initialize_logging
from utils.network import get_proxy
from utils.pidfile import PidFile
from utils.signals import SignalHandler

from dogstatsd import (
    Server,
    Reporter,
)
from dogstatsd.constants import (  # pylint: disable=no-name-in-module
    DOGSTATSD_FLUSH_INTERVAL,
    DOGSTATSD_AGGREGATOR_BUCKET_SIZE,
)

# Globals
PID_NAME = 'datadog-unix-agent.dogstatsd'

log = logging.getLogger('dogstatsd')


def init_config():
    config.add_search_path("/etc/datadog-agent")
    config.add_search_path(os.path.join(DEFAULT_PATH, "etc/datadog-agent"))
    config.add_search_path("./etc/datadog-agent")
    config.add_search_path(".")
    try:
        config.load()
        config.add_search_path(config.get('conf_path'))

        #  load again
        config.load()
    finally:
        initialize_logging('dogstatsd')


def init_dogstatsd(config):
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

class Dogstatsd(Daemon):
    COMMANDS = [
        'start',
        'stop',
    ]

    @classmethod
    def usage(cls):
        return "Usage: %s %s\n" % (sys.argv[0], "|".join(cls.COMMANDS))

    def run(self):
        reporter, server, forwarder = init_dogstatsd(config)

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
        try:
            server.start()
        except OSError as e:
            log.error("There was a problem starting the dogstatsd server %s", e)
            forwarder.stop()
            reporter.stop()

        reporter.join()
        logging.info("Dogstatsd reporter done...")

        handler.stop()
        handler.join()

        logging.info("Thank you for shopping at DataDog! Come back soon!")


def main(config_path=None):
    """ The main entry point for the unix version of dogstatsd. """
    COMMANDS_START_DOGSTATSD = [
        'start',
    ]

    parser = optparse.OptionParser("%prog [{commands}]".format(commands='|'.join(Dogstatsd.COMMANDS)))
    parser.add_option('-u', '--use-local-forwarder', action='store_true',
                      dest="use_forwarder", default=False)
    parser.add_option('-b', '--background', action='store_true', default=False,
                      dest='background', help='Run agent on the foreground')
    options, args = parser.parse_args()

    try:
        init_config()
    except Exception as e:
        logging.error("Problem initializing configuration: %s", e)
        return 1

    if (os.path.dirname(os.path.realpath(__file__)) != os.path.join(DEFAULT_PATH, 'agent')):
        log.info("""You don't seem to be running a package installed agent (expected
                 at %s). You may need to specify sane locations for your configs,
                 logs, run path, etc. And remember to drop the configuration
                 file in one of the supported locations.""" % DEFAULT_PATH)

    # If no args were passed in, run the server in the foreground.
    pid_dir = config.get('run_path')
    dogstatsd = Dogstatsd(PidFile(PID_NAME, pid_dir).get_path())

    foreground = not options.background
    command = 'start' if not args else args[0]
    if command in COMMANDS_START_DOGSTATSD:
        dogstatsd.start(foreground=foreground)
    elif command == 'stop':
        dogstatsd.stop()
    else:
        sys.stderr.write("Unknown command: %s\n\n" % command)
        parser.print_help()
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
