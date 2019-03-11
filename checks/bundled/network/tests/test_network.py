# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import time
from collections import namedtuple
from pathlib import PurePosixPath

import mock
import psutil

from aggregator import MetricsAggregator

import pytest

HOSTNAME = 'foo'
CHECK_NAME = 'network'

GAUGE = 'gauge'

net_counter = namedtuple('net_counter', ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv',
                                       'errin', 'errout', 'dropin', 'dropout'])
result = namedtuple('result', ['name', 'value', 'tags'])


MOCK_NET_COUNTERS = {
    'lo': net_counter(bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0,
                     errin=0, errout=0, dropin=0, dropout=0),
    'en0': net_counter(bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0,
                     errin=0, errout=0, dropin=0, dropout=0),
    'en1': net_counter(bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0,
                     errin=0, errout=0, dropin=0, dropout=0),
}

def mock_net_io_counters(pernic=False):
    return MOCK_NET_COUNTERS

def generate_expected_rates(attr_map):
    total_rates = 0
    expected_rates = {}
    for device, counter in MOCK_NET_COUNTERS.items():
        tag_set = ["device:{}".format(device)]
        for attr, metric in attr_map.items():
            metric = "system.net.{}".format(metric)
            value = getattr(counter, attr)
            # NOTE: all rates have a value of zero (ie. the delta = 0)
            if metric in expected_rates:
                expected_rates[metric].append(result(name=metric, value=0, tags=tag_set))
            else:
                expected_rates[metric] = [result(name=metric, value=0, tags=tag_set)]

            total_rates += 1

    return total_rates, expected_rates

def is_metric_expected(expectations, metric):
    name = metric['metric']
    tags = list(metric['tags'])

    if name not in expectations:
        return False

    metric_list = expectations[name]
    for m in metric_list:
        if sorted(tags) == sorted(m.tags) or \
                sorted(tags) == sorted([tag.encode('utf-8') for tag in m.tags]):
            if metric['points'][0][1] == m.value:
                return True

    return False

@mock.patch('psutil.net_io_counters', side_effect=mock_net_io_counters)
def test_network_basic(net_io_counters):
    from datadog_checks.network import Network  # delayed import for good patching

    aggregator = MetricsAggregator(
        HOSTNAME,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    total_rates, expected_rates = generate_expected_rates(Network.ATTR_MAP)

    c = Network("network", {}, {}, aggregator)
    c.check({})

    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric
    assert len(metrics) == 0  # all rates for now

    time.sleep(1)

    c.check({})
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    assert len(metrics) == total_rates
    for metric in metrics:
        assert metric['metric'] in expected_rates
        assert len(metric['points']) == 1
        assert metric['host'] == HOSTNAME
        assert metric['type'] == GAUGE
        assert is_metric_expected(expected_rates, metric)
