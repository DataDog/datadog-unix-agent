#!/usr/bin/env python

import json
import signal
import sys
import logging

from config import config
from forwarder import Forwarder
from utils.hostname import get_hostname
from metadata import get_metadata


def init_agent():
    # init default search path
    config.add_search_path("/etc/datadog-unix-agent")
    config.add_search_path(".")
    config.load()

    # init log
    level = logging.getLevelName(config.get("log_level").upper())
    logging.basicConfig(level=level)

def start():
    """
    Dummy start until we have a collector
    """
    init_agent()

    logging.info("Starting the agent, hostname: %s", get_hostname())

    # init Forwarder
    logging.info("Starting the Forwarder")
    f = Forwarder(config.get("api_key"), config.get("dd_url"))
    f.start()

    metadata = get_metadata(get_hostname())
    f.submit_v1_intake(json.dumps(metadata), {'Content-Type': 'application/json'})
    logging.info("metadata:\n%s", json.dumps(metadata))

    def signal_handler(signal, frame):
        logging.info("SIGINT received: stopping the agent")
        logging.info("Stopping the forwarder")
        f.stop()
        logging.info("See you !")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == "__main__":
    start()
