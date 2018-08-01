#!/usr/bin/env python

# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import signal
import sys
import time
import logging
from optparse import OptionParser
from threading import Thread, Event

from config import config
from config.providers import FileConfigProvider
from utils.logs import initialize_logging
from utils.hostname import HostnameException, get_hostname
from utils.daemon import Daemon
from utils.pidfile import PidFile
from utils.network import get_proxy
from utils.flare import Flare
from metadata import get_metadata

from collector import Collector
from aggregator import MetricsAggregator
from serialize import Serializer
from forwarder import Forwarder
from api import APIServer

# Globals
PID_NAME = 'datadog-unix-agent'
PID_DIR = None

log = logging.getLogger('agent')


class AgentRunner(Thread):
    def __init__(self, collector, serializer, config):
        super(AgentRunner, self).__init__()
        self._collector = collector
        self._serializer = serializer
        self._config = config
        self._event = Event()

    def collection(self):
        # update the metadata periodically?
        metadata = get_metadata(get_hostname())
        self._serializer.submit_metadata(metadata)

        while not self._event.is_set():
            self._collector.run_checks()
            self._serializer.serialize_and_push()
            time.sleep(self._config.get('min_collection_interval'))

    def stop(self):
        log.info('Stopping Agent Runner...')
        self._event.set()

    def run(self):
        log.info('Starting Agent Runner...')
        self.collection()


def init_config():
    # init default search path
    config.add_search_path("/etc/datadog-agent")
    config.add_search_path("./etc/datadog-agent")
    config.add_search_path(".")
    try:
        config.load()
        config.add_search_path(config.get('conf_path'))

        #  load again
        config.load()
    except Exception:
        initialize_logging('agent')
        raise

    # init log
    initialize_logging('agent')

    # add file provider
    file_provider = FileConfigProvider()
    file_provider.add_place(os.path.join(config.get('conf_path'), 'conf.d'))
    file_provider.add_place(config.get('additional_checksd'))
    config.add_provider('file', file_provider)

    # FIXME: do this elsewhere
    # collect config
    config.collect_check_configs()


class Agent(Daemon):
    COMMANDS = [
        'start',
        'stop',
        'restart',
        'status',
        'flare',
    ]

    @classmethod
    def usage(cls):
        return "Usage: %s %s\n" % (sys.argv[0], "|".join(cls.COMMANDS))

    @classmethod
    def info(cls):
        return True

    @classmethod
    def flare(cls, case_id):
        email = raw_input('Please enter your contact email address: ').lower()
        case_id = int(case_id) if case_id else None
        myflare = Flare(case_id=case_id, email=email)
        myflare.add_path(os.path.dirname(config.get('conf_path')))
        myflare.add_path(os.path.dirname(config.get('logging').get('agent_log_file')))
        myflare.add_path(os.path.dirname(config.get('logging').get('dogstatsd_log_file')))
        myflare.add_path(config.get('additional_checksd'))

        flarepath = myflare.create_archive()

        print 'The flare is going to be uploaded to Datadog'
        choice = raw_input('Do you want to continue [Y/n]? ')
        if choice.strip().lower() not in ['yes', 'y', '']:
            print 'Aborting (you can still use {0})'.format(flarepath)
            sys.exit(0)

        if myflare.submit():
            myflare.cleanup()

    def run(self):
        try:
            hostname = get_hostname()
        except HostnameException as e:
            logging.critical("{} - You can define one in datadog.yaml or in your hosts file".format(e))
            sys.exit(1)

        logging.info("Starting the agent, hostname: %s", hostname)

        # init Forwarder
        logging.info("Starting the Forwarder")
        api_key = config.get('api_key')
        dd_url = config.get('dd_url')
        if not dd_url:
            logging.error('No Datadog URL configured - cannot continue')
            sys.exit(1)
        if not api_key:
            logging.error('No API key configured - cannot continue')
            sys.exit(1)

        # get proxy settings
        proxies = get_proxy()
        logging.debug('Proxy configuration used: %s', proxies)

        forwarder = Forwarder(
            api_key,
            dd_url,
            proxies=proxies,
        )
        forwarder.start()

        # aggregator
        aggregator = MetricsAggregator(
            hostname,
            interval=config.get('aggregator_interval'),
            expiry_seconds=(config.get('min_collection_interval') +
                            config.get('aggregator_expiry_seconds')),
            recent_point_threshold=config.get('recent_point_threshold'),
            histogram_aggregates=config.get('histogram_aggregates'),
            histogram_percentiles=config.get('histogram_percentiles'),
        )

        # serializer
        serializer = Serializer(
            aggregator,
            forwarder,
        )

        # instantiate collector
        collector = Collector(config, aggregator)
        collector.load_check_classes()
        collector.instantiate_checks()

        # instantiate AgentRunner
        runner = AgentRunner(collector, serializer, config)

        # instantiate API
        api = APIServer(8888, aggregator.stats)

        def signal_handler(signal, frame):
            log.info("SIGINT received: stopping the agent")
            log.info("Stopping the forwarder")
            runner.stop()
            forwarder.stop()
            api.stop()
            log.info("See you !")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        runner.start()
        api.run()  # blocking tornado in main thread


def main():
    parser = OptionParser()
    parser.add_option('-b', '--background', action='store_true', default=False,
                      dest='background', help='Run agent on the foreground')
    options, args = parser.parse_args()

    if len(args) < 1:
        sys.stderr.write(Agent.usage())
        return 2

    command = args[0]
    if command not in Agent.COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    try:
        init_config()
    except Exception as e:
        logging.error("Problem initializing configuration: %s", e)
        return 1

    agent = Agent(PidFile(PID_NAME, PID_DIR).get_path())

    foreground = not options.background
    if 'start' == command:
        logging.info('Start daemon')
        agent.start(foreground=foreground)

    elif 'stop' == command:
        logging.info('Stop daemon')
        agent.stop()

    elif 'restart' == command:
        logging.info('Restart daemon')
        agent.restart()

    elif 'status' == command:
        agent.status()

    elif 'flare' == command:
        case_id = raw_input('Do you have a support case id? Please enter it here (otherwise just hit enter): ').lower()
        agent.flare(case_id)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StandardError:
        try:
            logging.exception("Uncaught error running the Agent")
        except Exception:
            pass
        raise
