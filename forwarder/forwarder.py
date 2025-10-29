# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import queue
import logging

from .worker import Worker, RetryWorker
from .transaction import Transaction
from config.default import DEFAULT_FORWARDER_TO
from utils.stats import Stats
from utils.http import get_shared_requests

log = logging.getLogger(__name__)


class Forwarder(object):

    V1_ENDPOINT = "/intake/"
    V1_SERIES_ENDPOINT = "/api/v1/series"
    V1_SERVICE_CHECKS_ENDPOINT = "/api/v1/check_run"

    DD_API_HEADER = "DD-API-KEY"

    QUEUES_SIZE = 100
    WORKER_JOIN_TIME = 2

    def __init__(self, api_key, domain, forwarder_timeout=DEFAULT_FORWARDER_TO, nb_worker=4):
        self.api_key = api_key
        self.domain = domain
        self.stats = Stats()
        self.input_queue = queue.Queue(self.QUEUES_SIZE)
        self.retry_queue = queue.Queue(self.QUEUES_SIZE)
        self.workers = []
        self.nb_worker = nb_worker
        self.retry_worker = None
        self.forwarder_timeout = forwarder_timeout
    # --------------------------------------------------------------------------
    # Lifecycle management
    # --------------------------------------------------------------------------
    def start(self):
        """Start retry worker and all forwarder workers."""
        self.retry_worker = RetryWorker(
            self.input_queue, self.retry_queue, self.stats)
        self.retry_worker.start()

        for i in range(self.nb_worker):
            w = Worker(self.input_queue, self.retry_queue, self.stats)
            w.start()
            self.workers.append(w)

    def stop(self):
        """Stop all workers gracefully."""
        self.retry_worker.stop()

        for w in self.workers:
            w.stop()

        self.retry_worker.join(self.WORKER_JOIN_TIME)
        if self.retry_worker.is_alive():
            log.error("Could not stop thread '%s'", self.retry_worker.name)
        self.retry_worker = None

        for w in self.workers:
            # wait 2 seconds for the worker to stop
            w.join(self.WORKER_JOIN_TIME)
            if w.is_alive():
                log.error("Could not stop thread '%s'", w.name)
        self.workers = []

    # --------------------------------------------------------------------------
    # Internal payload submission helper
    # --------------------------------------------------------------------------
    def _submit_payload(self, endpoint, payload, extra_headers=None):
        """Create and enqueue a Transaction for the given payload and endpoint."""
        shared_requests = get_shared_requests()
        base_options = shared_requests.options.copy()
        base_options["timeout"] = self.forwarder_timeout

        # Build headers for this transaction
        headers = base_options.get("headers", {}).copy()
        headers[self.DD_API_HEADER] = self.api_key
        if extra_headers:
            headers.update(extra_headers)
        base_options["headers"] = headers

        # Create the transaction
        t = Transaction(payload, self.domain, endpoint, options=base_options)

        try:
            self.input_queue.put_nowait(t)
        except queue.Full as e:
            log.error(
                "Could not submit transaction to '%s', queue is full (dropping it): %s",
                endpoint,
                e,
            )

    # --------------------------------------------------------------------------
    # Public submission helpers
    # --------------------------------------------------------------------------
    def submit_v1_series(self, payload, extra_headers=None):
        self.stats.inc_stat("series_payloads", 1)
        self._submit_payload(self.V1_SERIES_ENDPOINT, payload, extra_headers)

    def submit_v1_intake(self, payload, extra_headers=None):
        self.stats.inc_stat("intake_payloads", 1)
        self._submit_payload(self.V1_ENDPOINT, payload, extra_headers)

    def submit_v1_service_checks(self, payload, extra_headers=None):
        self.stats.inc_stat("service_check_payloads", 1)
        self._submit_payload(
            self.V1_SERVICE_CHECKS_ENDPOINT, payload, extra_headers)
