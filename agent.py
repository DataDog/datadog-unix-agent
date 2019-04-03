#!/opt/datadog-agent/embedded/bin/python

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

import requests
import requests.exceptions
from jinja2 import Environment, FileSystemLoader

from config import config
from config.providers import FileConfigProvider
from config.default import DEFAULT_PATH

from utils.logs import initialize_logging
from utils.hostname import HostnameException, get_hostname
from utils.daemon import Daemon
from utils.signals import SignalHandler
from utils.pidfile import PidFile
from utils.network import get_proxy
from utils.flare import Flare
from metadata import get_metadata

from collector import Collector
from aggregator import MetricsAggregator
from serialize import Serializer
from forwarder import Forwarder
from api import APIServer

from dogstatsd.helpers import (
    init_dogstatsd,
    DogstatsdRunner,
)


# Globals
AGENT_VERSION = '0.8.0'
PID_NAME = 'datadog-unix-agent'

log = logging.getLogger('agent')


class AgentRunner(Thread):
    def __init__(self, collector, serializer, config):
        super(AgentRunner, self).__init__()
        self._collector = collector
        self._serializer = serializer
        self._config = config
        self._event = Event()
        self._meta_ts = None

    def collection(self):
        while not self._event.is_set():
            try:
                current_ts = time.monotonic()

                if self._meta_ts is None or (current_ts - self._meta_ts) >= self._config.get('host_metadata_interval'):
                    metadata = get_metadata(get_hostname(), AGENT_VERSION, start_event=(self._meta_ts is None))
                    self._serializer.submit_metadata(metadata)
                    self._meta_ts = current_ts

                self._collector.run_checks()
                self._serializer.serialize_and_push()
            except Exception as e:
                log.exception("Unexpected error in last collection run")

            time.sleep(self._config.get('min_collection_interval'))

    def stop(self):
        log.info('Stopping Agent Runner...')
        self._event.set()

    def run(self):
        log.info('Starting Agent Runner...')
        self.collection()


def init_config(do_log=True):
    # init default search path
    config.add_search_path("/etc/datadog-agent")
    config.add_search_path(os.path.join(DEFAULT_PATH, "etc/datadog-agent"))
    config.add_search_path("./etc/datadog-agent")
    config.add_search_path(".")
    try:
        config.load()
    except Exception:
        if do_log:
            initialize_logging('agent')
        raise

    # init log
    if do_log:
        initialize_logging('agent')

    # add file provider
    file_provider = FileConfigProvider()
    file_provider.add_place(os.path.join(os.path.dirname(config.get_loaded_config()), 'conf.d'))
    file_provider.add_place(os.path.join(config.get('conf_path'), 'conf.d'))
    file_provider.add_place(config.get('additional_checksd'))
    config.add_provider('file', file_provider)

    # FIXME: perhaps do this elsewhere
    config.collect_check_configs()


class Agent(Daemon):
    # dictionary k:v - command:log
    COMMANDS = {
        'start': True,
        'stop': True,
        'restart': False,
        'status': False,
        'flare': False,
    }

    COMPONENTS = [
        'agent',
        'dogstatsd',
    ]

    STATUS_TIMEOUT = 5

    @classmethod
    def usage(cls):
        return "Usage: %s %s\n" % (sys.argv[0], "|".join(cls.COMMANDS.keys()))

    @classmethod
    def status(cls, config, to_screen=True):
        status = {}
        rendered = None
        api_addr = config['api']['bind_host']
        api_port = config['api']['port']
        for component in cls.COMPONENTS:
            if component == 'dogstatsd' and not config['dogstatsd']['enable']:
                continue

            target = 'http://{host}:{port}/status/{component}'.format(
                host=api_addr, port=api_port, component=component)
            try:
                r = requests.get(target, timeout=cls.STATUS_TIMEOUT)
                r.raise_for_status()

                status[component] = r.json()
            except requests.exceptions.HTTPError as e:
                log.error("HTTP error collecting agent status: {}".format(e))
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                log.error("Problem connecting or connection timed out, is the agent up? Error: {}".format(e))

        if status:
            here = os.path.dirname(os.path.realpath(__file__))
            templates = os.path.join(here, 'templates')
            template_env = Environment(loader=FileSystemLoader(templates))
            template = template_env.get_template('status.jinja')
            rendered = template.render(version=AGENT_VERSION, status=status)
            if to_screen:
                print(rendered)

        return rendered

    @classmethod
    def flare(cls, case_id):
        email = input('Please enter your contact email address: ').lower()
        case_id = int(case_id) if case_id else None
        myflare = Flare(case_id=case_id, email=email)
        myflare.add_path(config.get('conf_path'))
        myflare.add_path(config.get_loaded_config())
        myflare.add_path(config.get('logging').get('agent_log_file'))
        myflare.add_path(config.get('logging').get('dogstatsd_log_file'))
        myflare.add_path(config.get('additional_checksd'))

        flarepath = myflare.create_archive(status=cls.status(to_screen=False))

        print('The flare is going to be uploaded to Datadog')
        choice = input('Do you want to continue [Y/n]? ')
        if choice.strip().lower() not in ['yes', 'y', '']:
            print('Aborting (you can still use {0})'.format(flarepath))
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

        # instantiate Dogstatsd
        reporter = None
        dogstatsd = None

        dsd_enable = config['dogstatsd'].get('enable', False)
        dsd_server = None
        if dsd_enable:
            reporter, dsd_server, _ = init_dogstatsd(config, forwarder=forwarder)
            dsd = DogstatsdRunner(dsd_server)

        # instantiate API
        api = APIServer(config, collector, aggregator.stats, dsd_server.aggregator.stats if dsd_server else None)

        handler = SignalHandler()
        # components
        handler.register('runner', runner)
        handler.register('forwarder', forwarder)
        handler.register('api', api)
        if dsd_enable:
            handler.register('reporter', reporter)
            handler.register('dsd_server', dsd_server)

        # signals
        handler.handle(signal.SIGTERM)
        handler.handle(signal.SIGINT)

        # start signal handler
        handler.start()

        runner.start()
        api.start()

        if dsd_enable:
            reporter.start()
            dsd.start()

            dsd.join()
            logging.info("Dogstatsd server done...")
            try:
                dsd.raise_for_status()
            except Exception as e:
                log.error("There was a problem with the dogstatsd server: %s", e)
                reporter.stop()

        runner.join()
        logging.info("Collector done...")

        api.join()
        logging.info("API done...")

        handler.stop()
        handler.join()
        logging.info("Signal handler done...")

        logging.info("Thank you for shopping at DataDog! Come back soon!")

        sys.exit(0)


def main():
    parser = OptionParser()
    parser.add_option('-b', '--background', action='store_true', default=False,
                      dest='background', help='Run agent on the foreground')
    parser.add_option('-l', '--force-logging', action='store_true', default=False,
                      dest='logging', help='force logging')
    options, args = parser.parse_args()

    if len(args) < 1:
        sys.stderr.write(Agent.usage())
        return 2

    command = args[0]
    if command not in Agent.COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    try:
        do_log = options.logging or Agent.COMMANDS[command]
        init_config(do_log=do_log)
    except Exception as e:
        logging.error("Problem initializing configuration: %s", e)
        return 1

    if (os.path.dirname(os.path.realpath(__file__)) != os.path.join(DEFAULT_PATH, 'agent')):
        log.info("""You don't seem to be running a package installed agent (expected
                 at %s). You may need to specify sane locations for your configs,
                 logs, run path, etc. And remember to drop the configuration
                 file in one of the supported locations.""" % DEFAULT_PATH)

    pid_dir = config.get('run_path')
    agent = Agent(PidFile(PID_NAME, pid_dir).get_path())

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
        agent.status(config)

    elif 'flare' == command:
        case_id = input('Do you have a support case id? Please enter it here (otherwise just hit enter): ').lower()
        agent.flare(case_id)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        try:
            logging.exception("Uncaught error running the Agent")
        except Exception:
            pass
        raise
