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
from metadata import get_metadata

from collector import Collector
from aggregator import MetricsAggregator
from serialize import Serializer
from forwarder import Forwarder


def init_agent():
    # init default search path
    config.add_search_path("/etc/datadog-unix-agent")
    config.add_search_path(".")
    config.load()

    # add file provider
    file_provider = FileConfigProvider()
    file_provider.add_place(config.get('additional_checksd'))
    config.add_provider('file', file_provider)

    # FIXME: do this elsewhere
    # collect config
    config.collect_check_configs()

    # init log
    level = logging.getLevelName(config.get("log_level").upper())
    logging.basicConfig(level=level)


def start():
    """
    Dummy start until we have a collector
    """
    init_agent()

    hostname = get_hostname()

    logging.info("Starting the agent, hostname: %s", hostname)

    # init Forwarder
    domains = [config.get('dd_url', 'https://localhost:9999')]
    logging.info("Starting the Forwarder")
    forwarder = Forwarder(
        config.get('api_key', 'fake_api'),
        domains
    )
    forwarder.start()

    # aggregator
    aggregator = MetricsAggregator(
        hostname,
        interval=config.get('histogram_aggregates', 1.0),
        histogram_aggregates=config.get('histogram_aggregates'),
        histogram_percentiles=config.get('histogram_percentiles'),
    )

    # serializer
    serializer = Serializer(
        aggregator,
        forwarder,
    )

    # update the metadata periodically?
    metadata = get_metadata(hostname)
    serializer.set_metadata(metadata)

    # instantiate collector
    collector = Collector(config, aggregator)
    collector.instantiate_checks()

    def signal_handler(signal, frame):
        logging.info("SIGINT received: stopping the agent")
        logging.info("Stopping the forwarder")
        forwarder.stop()
        logging.info("See you !")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    serializer.submit_metadata()
    while True:
        collector.run_checks()
        serializer.serialize_and_push()
        time.sleep(config.get('min_collection_interval'))


if __name__ == "__main__":
    start()
