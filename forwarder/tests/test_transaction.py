# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import time
import requests_mock

from forwarder.transaction import Transaction

def test_transaction_creation():
    start = time.time()
    t = Transaction("data", "https://datadog.com", "/v1/series", {"DD": "true", "Content-Type": "application/json"})
    assert t.payload == "data"
    assert t.domain == "https://datadog.com"
    assert t.endpoint == "/v1/series"
    assert t.headers == {"DD": "true", "Content-Type": "application/json"}
    assert t.nb_try == 0
    assert t.timeout == 20 # default value from config

    # test created_at value
    assert t.created_at >= start
    assert t.created_at <= time.time()

def test_get_endpoint():
    t = Transaction("data", "https://datadog.com", "/v1/series", None)
    assert t.get_endpoint() == "/v1/series"

    t = Transaction("data", "https://datadog.com", "/series?api_key=abcdefghijklmnopqrstuvwxyz012345", None)
    assert t.get_endpoint() == "/series?api_key=***************************12345"

    t = Transaction("data", "https://datadog.com", "/series?test=21&api_key=abcdefghijklmnopqrstuvwxyz012345", None)
    assert t.get_endpoint() == "/series?test=21&api_key=***************************12345"

    t = Transaction("data", "https://datadog.com", "/series?api_key=test1234", None)
    assert t.get_endpoint() == "/series?api_key=***************************t1234"

    t = Transaction("data", "https://datadog.com", "/series?api_key=test", None)
    assert t.get_endpoint() == "/series?api_key=test"

def test_reschedule():
    t = Transaction("data", "https://datadog.com", "/", None)

    # on the first try "reschedule" should set next_flush to "now"
    before = time.time()
    t.reschedule()
    after = time.time()
    assert t.next_flush is not None
    assert t.next_flush >= before
    assert t.next_flush <= after

    t = Transaction("data", "https://datadog.com", "/", None)
    t.nb_try = 2
    before = time.time()
    t.reschedule()
    after = time.time()
    assert t.next_flush is not None
    assert t.next_flush >= before + 2 * Transaction.RETRY_INTERVAL
    assert t.next_flush <= after + 2 * Transaction.RETRY_INTERVAL

    t = Transaction("data", "https://datadog.com", "/", None)
    t.nb_try = 10000
    before = time.time()
    t.reschedule()
    after = time.time()
    assert t.next_flush is not None
    assert t.next_flush >= before + Transaction.MAX_RETRY_INTERVAL
    assert t.next_flush <= after + Transaction.MAX_RETRY_INTERVAL

def test_process_success(m):
    m.post("https://datadog.com/v1/series", additional_matcher=lambda r: r.text == "data")
    t = Transaction("data", "https://datadog.com", "/v1/series", None)
    assert t.process()
    assert t.nb_try == 1

def test_process_error(m):
    t = Transaction("data", "https://datadog.com", "/v1/series", {"test": "21"})
    headers = {"test": "21"}

    nb_try = 1
    for err_code in [400, 403, 404, 413]:
        m.post("https://datadog.com/v1/series",
                status_code=err_code,
                headers=headers,
                additional_matcher=lambda r: r.text == "data")
        assert t.process()
        assert t.nb_try == nb_try
        nb_try += 1

    m.post("https://datadog.com/v1/series",
            status_code=402,
            headers=headers,
            additional_matcher=lambda r: r.text == "data")
    assert not t.process()
    assert t.nb_try == nb_try
