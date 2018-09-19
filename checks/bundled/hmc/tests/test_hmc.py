# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
from mock import patch
import psutil

from datadog_checks.hmc import HMC
from aggregator import MetricsAggregator

import pytest

HOSTNAME = 'foo'
CHECK_NAME = 'hmc'

def get_config_stubs():
    return [{
        'instance': {
            'name': 'test_0',
            'host': 'foo',
            'port': 22,
            'username': 'bruce_banner',
            'password': None,
            'private_key_file': 'id_rsa',
            'private_key_type': 'rsa',
            'add_missing_keys': [],
        }
    }]

class MockParamiko(object):
    def __init__(self):
        self.pid = None

    def is_running(self):
        return True

    def children(self, recursive=False):
        return []


@pytest.fixture
def aggregator():
    aggregator = MetricsAggregator(
        HOSTNAME,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    return aggregator


def test_psutil_wrapper_simple_fail(aggregator):
    # Load check with empty config
    pass

