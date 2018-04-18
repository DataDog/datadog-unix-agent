# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging
import threading

from utils.hostname import get_hostname


class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated metrics to the
    server.
    """
    EVENT_CHUNK_SIZE = 50

    def __init__(self, interval, aggregator, serializer,
                 api_key=None, use_watchdog=False, hostname=None):
        threading.Thread.__init__(self)
        self.interval = int(interval)
        self.finished = threading.Event()
        self.aggregator = aggregator
        self.serializer = serializer
        self.flush_count = 0
        self.log_count = 0
        self.hostname = hostname or get_hostname()
        self.api_key = api_key

    def stop(self):
        logging.info("Stopping reporter")
        self.finished.set()

    def run(self):

        logging.info("Reporting every %ss" % self.interval)

        while not self.finished.isSet():  # Use camel case isSet for 2.4 support.
            self.finished.wait(self.interval)
            self.aggregator.send_packet_count('datadog.dogstatsd.packet.count')
            self.flush()
            if self.watchdog:
                self.watchdog.reset()

        # Clean up the status messages.
        logging.debug("Stopped reporter")

    def flush(self):
        try:
            self.flush_count += 1
            metric_count, event_count, service_check_count = self.submit()

            logging.debug("Flush #%s: flushed %s metric(s), %s event(s), and %s service check(s)" %
                          (self.flush_count, metric_count, event_count, service_check_count))

        except Exception:
            if self.finished.isSet():
                logging.debug("Couldn't flush metrics, but that's expected as we're stopping")
            else:
                logging.exception("Error flushing metrics")

    def submit(self):
        return self.serializer.serialize_and_push()
