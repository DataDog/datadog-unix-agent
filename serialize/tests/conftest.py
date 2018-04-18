# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import json

import pytest
from mock import MagicMock

HERE = os.path.dirname(os.path.realpath(__file__))
FIXTURE_PATH = os.path.join(HERE, 'fixtures')

MOCK_FLUSH_DATA = [
    {'foo': 'bar'},
    {'haz': 'qux'}
]


@pytest.fixture(scope='session')
def mock_aggregator():
    aggregator = MagicMock()
    series = {
        'series': MOCK_FLUSH_DATA
    }
    events = MOCK_FLUSH_DATA
    service_checks = MOCK_FLUSH_DATA

    attrs = {
        'series': series,
        'events': events,
        'service_checks': service_checks,
        'flush.return_value': MOCK_FLUSH_DATA,
        'flush_events.return_value': events,
        'flush_service_checks.return_value': service_checks,
    }
    aggregator.configure_mock(**attrs)
    return aggregator


@pytest.fixture(scope='session')
def mock_forwarder():
    return MagicMock()


@pytest.fixture(scope='session')
def legacy_payload():
    with open(FIXTURE_PATH + '/legacy_payload.json') as f:
        legacy_payload = json.load(f)

    return legacy_payload


@pytest.fixture(scope='session')
def service_check_payload():
    with open(FIXTURE_PATH + '/sc_payload.json') as f:
        service_check_payload = json.load(f)

    return service_check_payload
