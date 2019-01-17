# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import requests_mock
import queue
import time

from forwarder.worker import Worker, RetryWorker
from forwarder.transaction import Transaction


def test_init():
    input_queue = queue.Queue(2)
    retry_queue = queue.Queue(2)
    w = Worker(input_queue, retry_queue)

    assert w.input_queue == input_queue
    assert w.retry_queue == retry_queue

    rw = RetryWorker(input_queue, retry_queue)

    assert rw.input_queue == input_queue
    assert rw.retry_queue == retry_queue
    assert rw.transactions == []
    assert rw.flush_interval == rw.DEFAULT_FLUSH_INTERVAL
    assert rw.retry_queue_max_size == 30 # default value from config

@requests_mock.mock()
def test_worker_process_transactions(m):
    input_queue = queue.Queue(2)
    retry_queue = queue.Queue(2)
    w = Worker(input_queue, retry_queue)

    t_success = Transaction("data", "https://datadog.com", "/success", None)
    t_error = Transaction("data", "https://datadog.com", "/error", None)
    m.post("https://datadog.com/success", status_code=200)
    m.post("https://datadog.com/error", status_code=402)

    input_queue.put(t_success)
    input_queue.put(t_error)

    # process 2 transactions
    w._process_transactions()
    w._process_transactions()

    assert input_queue.empty()
    assert not retry_queue.empty()

    assert t_success.nb_try == 1
    assert t_error.nb_try == 1
    assert t_error.next_flush is not None

    retry_item = retry_queue.get()
    assert t_error == retry_item

def test_worker_stop():
    input_queue = queue.Queue()
    retry_queue = queue.Queue()
    w = Worker(input_queue, retry_queue)
    w.start()

    w.stop()
    w.join(2)
    assert not w.isAlive()

def test_retry_worker_flush():
    input_queue = queue.Queue(1)
    retry_queue = queue.Queue(1)
    w = RetryWorker(input_queue, retry_queue)

    t_ready = Transaction("data", "https://datadog.com", "/success", None)
    t_ready.next_flush = time.time() - 10
    w.transactions.append(t_ready)

    t_not_ready = Transaction("data", "https://datadog.com", "/success", None)
    t_not_ready.next_flush = time.time() + 1000
    w.transactions.append(t_not_ready)

    w._flush_transactions()
    assert len(w.transactions) == 1
    assert w.transactions[0] == t_not_ready

    try:
        t = input_queue.get_nowait()
    except Exception:
        # we should not fail to get a transaction
        raise Exception("input_queue should not be empty")
    assert t == t_ready

def test_retry_worker_process_transaction():
    input_queue = queue.Queue(2)
    retry_queue = queue.Queue(2)

    w = RetryWorker(input_queue, retry_queue, flush_interval=1)

    # test pulling 1 transaction without flushing
    t1 = Transaction("data", "https://datadog.com", "/success", None)
    t1.next_flush = time.time()
    retry_queue.put(t1)

    w.GET_TIMEOUT = 10
    base_flush_time = time.time() + 10
    flush_time = w._process_transactions(base_flush_time)
    end = time.time()

    assert flush_time == base_flush_time
    assert retry_queue.qsize() == 0
    assert len(w.transactions) == 1
    assert w.transactions[0] == t1

    # now test with flush
    w.GET_TIMEOUT = 0.1
    start = time.time()
    flush_time = w._process_transactions(0)
    end = time.time()

    assert len(w.transactions) == 0
    try:
        t = input_queue.get(True, 1)
    except queue.Empty:
        raise Exception("input_queue should not be empty")
    assert t == t1

    assert flush_time >= start + 1
    assert flush_time <= end + 1

def test_retryworker_stop():
    input_queue = queue.Queue()
    retry_queue = queue.Queue()
    w = RetryWorker(input_queue, retry_queue)
    w.start()

    w.stop()
    w.join(2)
    assert not w.isAlive()
