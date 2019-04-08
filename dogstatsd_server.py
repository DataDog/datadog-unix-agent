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

from config import config
from config.default import DEFAULT_PATH
from utils.daemon import Daemon
from utils.logs import initialize_logging
from utils.pidfile import PidFile
from utils.signals import SignalHandler

from dogstatsd.helpers import (
    init_dogstatsd,
    DogstatsdRunner,
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

        dsd = DogstatsdRunner(server)

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
        forwarder.start()
        reporter.start()
        dsd.start()

        dsd.join()
        logging.info("Dogstatsd server done...")
        try:
            dsd.raise_for_status()
        except Exception as e:
            log.error("There was a problem with the dogstatsd server: %s", e)
            reporter.stop()
            forwarder.stop()

        reporter.join()
        logging.info("Dogstatsd reporter done...")

        handler.stop()
        handler.join()
        logging.info("Signal handler done...")

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
