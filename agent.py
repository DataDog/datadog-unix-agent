#!/usr/bin/env python

# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import signal
import sys
import time
import logging

from config import config
from config.providers import FileConfigProvider
from utils.hostname import get_hostname
from utils.daemon import Daemon
from utils.pidfile import PidFile
from metadata import get_metadata

from collector import Collector
from aggregator import MetricsAggregator
from serialize import Serializer
from forwarder import Forwarder

PID_NAME = "dd-unix-agent"
PID_DIR = None


def init_config():
    # init default search path
    config.add_search_path("/etc/datadog-unix-agent")
    config.add_search_path(".")
    config.load()

    # init log
    level = logging.getLevelName(config.get("log_level").upper())
    logging.basicConfig(level=level)

    # add file provider
    file_provider = FileConfigProvider()
    file_provider.add_place(config.get('additional_checksd'))
    config.add_provider('file', file_provider)

    # FIXME: do this elsewhere
    # collect config
    config.collect_check_configs()


class Agent(Daemon):
    @classmethod
    def info(cls):
        return True

    def run(self):
        hostname = get_hostname()

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

        forwarder = Forwarder(
            api_key,
            dd_url
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

        def signal_handler(signal, frame):
            logging.info("SIGINT received: stopping the agent")
            logging.info("Stopping the forwarder")
            forwarder.stop()
            logging.info("See you !")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        # update the metadata periodically?
        metadata = get_metadata(hostname)
        serializer.submit_metadata(metadata)
        while True:
            collector.run_checks()
            serializer.serialize_and_push()
            time.sleep(config.get('min_collection_interval'))


def main():
    init_config()

    agent = Agent(PidFile(PID_NAME, PID_DIR).get_path())
    agent.start(foreground=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StandardError:
        try:
            logging.exception("Uncaught error running the Agent")
        except Exception:
            pass
        raise
