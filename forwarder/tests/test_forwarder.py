# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import queue

from forwarder import Forwarder
from config import config
from config.config import AGENT_VERSION


DOMAIN = "https://app.datadoghq.com"
TIMEOUT = config.get("forwarder_timeout")

def test_forwarder_creation():
    f = Forwarder("api_key", DOMAIN, TIMEOUT)
    assert f.api_key == "api_key"
    assert f.domain == "https://app.datadoghq.com"

def test_forwarder_start_stop():
    f = Forwarder("api_key", "https://datadog.com", TIMEOUT, 2)
    f.start()

    assert len(f.workers) == 2
    assert f.workers[0].is_alive()
    assert f.workers[1].is_alive()
    assert f.retry_worker.is_alive()

    tmp_workers = f.workers
    tmp_retry_worker = f.retry_worker

    f.stop()

    assert len(f.workers) == 0
    assert f.retry_worker is None
    assert not tmp_workers[0].is_alive()
    assert not tmp_workers[1].is_alive()
    assert not tmp_retry_worker.is_alive()

def get_transaction(f):
    try:
        return f.input_queue.get(True, 1)
    except queue.Empty:
        raise Exception("input_queue should not be empty")

def test_submit_payload_():
    f = Forwarder("api_key", DOMAIN, TIMEOUT)

    # case 1: extra headers provided
    f._submit_payload("test", "data", {"test": 21})
    t = get_transaction(f)
    assert t.payload == "data"
    assert t.domain == DOMAIN
    assert t.endpoint == "test"

    expected_headers = {
        "User-Agent": f"datadog-unix-agent/{AGENT_VERSION}",
        "test": 21,
        Forwarder.DD_API_HEADER: "api_key",
    }
    for k, v in expected_headers.items():
        assert t.options["headers"][k] == v

    # case 2: no extra headers
    f._submit_payload("test", "data")
    t = get_transaction(f)
    assert t.payload == "data"
    assert t.domain == DOMAIN
    assert t.endpoint == "test"

    expected_headers = {
        "User-Agent": f"datadog-unix-agent/{AGENT_VERSION}",
        Forwarder.DD_API_HEADER: "api_key",
    }
    for k, v in expected_headers.items():
        assert t.options["headers"][k] == v

def test_submit_v1_series():
    f = Forwarder("api_key", DOMAIN, TIMEOUT)
    f.submit_v1_series("data", None)
    t = get_transaction(f)

    assert t.endpoint == "/api/v1/series"
    assert t.payload == "data"

def test_submit_v1_service_checks():
    f = Forwarder("api_key", DOMAIN, TIMEOUT)
    f.submit_v1_service_checks("data", None)
    t = get_transaction(f)

    assert t.endpoint == "/api/v1/check_run"
    assert t.payload == "data"
