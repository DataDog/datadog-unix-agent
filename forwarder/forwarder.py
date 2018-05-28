# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import Queue
import logging

from worker import Worker, RetryWorker
from transaction import Transaction

log = logging.getLogger(__name__)


class Forwarder(object):

    V1_ENDPOINT = "/intake/"
    V1_SERIES_ENDPOINT = "/api/v1/series"
    V1_SERVICE_CHECKS_ENDPOINT = "/api/v1/check_run"

    DD_API_HEADER = "DD-Api-Key"

    QUEUES_SIZE = 100
    WORKER_JOIN_TIME = 2

    def __init__(self, api_key, domain, nb_worker=4, proxies={}):
        self.api_key = api_key
        self.domain = domain
        self.input_queue = Queue.Queue(self.QUEUES_SIZE)
        self.retry_queue = Queue.Queue(self.QUEUES_SIZE)
        self.workers = []
        self.nb_worker = nb_worker
        self.retry_worker = None
        self.proxies = {}

    def start(self):
        self.retry_worker = RetryWorker(self.input_queue, self.retry_queue)
        self.retry_worker.start()

        for i in range(self.nb_worker):
            w = Worker(self.input_queue, self.retry_queue)
            w.start()
            self.workers.append(w)

    def stop(self):
        self.retry_worker.stop()

        for w in self.workers:
            w.stop()

        self.retry_worker.join(self.WORKER_JOIN_TIME)
        if self.retry_worker.is_alive():
            log.errorf("Could not stop thread '%s'", self.retry_worker.name)
        self.retry_worker = None

        for w in self.workers:
            # wait 2 seconds for the worker to stop
            w.join(self.WORKER_JOIN_TIME)
            if w.is_alive():
                log.errorf("Could not stop thread '%s'", w.name)
        self.workers = []

    def _submit_payload(self, endpoint, payload, extra_header=None):
        endpoint += "?api_key=" + self.api_key

        if extra_header:
            extra_header[self.DD_API_HEADER] = self.api_key
        else:
            extra_header = {self.DD_API_HEADER: self.api_key}

        t = Transaction(payload, self.domain, endpoint, extra_header, proxies=self.proxies)
        try:
            self.input_queue.put_nowait(t)
        except Queue.Full as e:
            log.errorf("Could not submit transaction to '%s', queue is full (dropping it): %s", endpoint, e)

    def submit_v1_series(self, payload, extra_header):
        self._submit_payload(self.V1_SERIES_ENDPOINT, payload, extra_header)

    def submit_v1_intake(self, payload, extra_header):
        self._submit_payload(self.V1_ENDPOINT, payload, extra_header)

    def submit_v1_service_checks(self, payload, extra_header):
        self._submit_payload(self.V1_SERVICE_CHECKS_ENDPOINT, payload, extra_header)
