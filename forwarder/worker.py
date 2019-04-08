# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from threading import Thread, Event
import queue
import time
import logging

from config import config

log = logging.getLogger(__name__)

class Worker(Thread):

    def __init__(self, input_queue, retry_queue, stats):
        super(Worker, self).__init__()
        self.input_queue = input_queue
        self.retry_queue = retry_queue
        self.exit = Event()
        self._stats = stats

    def stop(self):
        self.exit.set()

    def _process_transactions(self):
        try:
            # blocking for 1 seconds so we can check the exit condition
            t = self.input_queue.get(True, 1)
        except queue.Empty:
            return

        try:
            success = t.process()
            if not success:
                t.reschedule()
                try:
                    self.retry_queue.put_nowait(t)
                    self._stats.inc_stat('transactions_rescheduled', 1)
                except queue.Full as e:
                    log.error("Could not retry transaction to '%s', queue is full (dropping it): %s", t.get_endpoint(), e)
                    self._stats.inc_stat('queue_full_errors', 1)
            else:
                self._stats.inc_stat('transactions_success', 1)
        except Exception as e:
            log.exception("unknown error processing transaction")

    def run(self):
        while not self.exit.is_set():
            self._process_transactions()

class RetryWorker(Worker):

    DEFAULT_FLUSH_INTERVAL = 5 # seconds
    GET_TIMEOUT = 1 # seconds

    def __init__(self, input_queue, retry_queue, stats, flush_interval=DEFAULT_FLUSH_INTERVAL):
        super(RetryWorker, self).__init__(input_queue, retry_queue, stats)
        self.transactions = []
        self.flush_interval = flush_interval
        self.retry_queue_max_size = config.get("forwarder_retry_queue_max_size")

    def _flush_transactions(self):
        if not self.transactions:
            return

        self.transactions.sort(key=lambda t: t.created_at, reverse=True)
        now = time.time()

        keep = []
        for t in self.transactions:
            if t.next_flush and t.next_flush > now:
                keep.append(t)
                continue

            try:
                self.input_queue.put_nowait(t)
            except queue.Full:
                log.error("Can't retry connection, input queue is full: dropping transaction")

        self.transactions = keep[:self.retry_queue_max_size]

    def _process_transactions(self, flush_time):
        try:
            t = self.retry_queue.get(True, self.GET_TIMEOUT)
        except queue.Empty:
            pass
        else:
            self.transactions.append(t)

        if flush_time <= time.time():
            self._flush_transactions()
            # set the next flush time
            flush_time = time.time() + self.flush_interval

        return flush_time

    def run(self):
        flush_time = time.time() + self.flush_interval

        while not self.exit.is_set():
            flush_time = self._process_transactions(flush_time)
