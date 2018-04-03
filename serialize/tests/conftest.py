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


class MockAggregator(object):
    def __init__(self):
        self.series = {
            'series': MOCK_FLUSH_DATA
        }
        self.events = {
            'events': MOCK_FLUSH_DATA
        }
        self.service_checks = {
            'service_checks': MOCK_FLUSH_DATA
        }

    def flush(self):
        return self.series

    def flush_events(self):
        return self.events

    def flush_service_checks(self):
        return self.service_checks


@pytest.fixture(scope='session')
def mock_aggregator():
    return MockAggregator()


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
