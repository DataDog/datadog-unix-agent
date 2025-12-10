# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.

import time
from collections import namedtuple
import mock

from aggregator import MetricsAggregator
from checks.corechecks.net.network.network import NetworkCheck


HOSTNAME = 'foo'
CHECK_NAME = 'network'
GAUGE = 'gauge'

net_counter = namedtuple(
    'net_counter',
    ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv',
     'errin', 'errout', 'dropin', 'dropout']
)

MOCK_NET_COUNTERS = {
    'lo': net_counter(0, 0, 0, 0, 0, 0, 0, 0),
    'en0': net_counter(0, 0, 0, 0, 0, 0, 0, 0),
    'en1': net_counter(0, 0, 0, 0, 0, 0, 0, 0),
}


def mock_net_io_counters(pernic=False):
    return MOCK_NET_COUNTERS


def generate_expected_rates(attr_map):
    total_rates = 0
    expected_rates = {}

    result = namedtuple('result', ['name', 'value', 'tags'])

    for device in MOCK_NET_COUNTERS:
        tags = ["device:{}".format(device)]
        for _, metric in attr_map.items():
            full_metric = "system.net.{}".format(metric)

            entry = result(full_metric, 0, tags)

            expected_rates.setdefault(full_metric, []).append(entry)
            total_rates += 1

    return total_rates, expected_rates


def is_metric_expected(expectations, metric):
    name = metric['metric']
    tags = [t.decode('utf-8') for t in metric['tags']]

    if name not in expectations:
        return False

    for expected in expectations[name]:
        if sorted(tags) == sorted(expected.tags) and metric['points'][0][1] == expected.value:
            return True

    return False


@mock.patch('psutil.net_io_counters', side_effect=mock_net_io_counters)
def test_network_basic(net_io_counters):
    aggregator = MetricsAggregator(
        HOSTNAME,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    total_rates, expected_rates = generate_expected_rates(NetworkCheck.ATTR_MAP)

    c = NetworkCheck("network", {}, {}, aggregator)
    c.check({})

    metrics = c.aggregator.flush()[:-1]
    assert len(metrics) == 0  # first run produces no rates

    time.sleep(1)

    c.check({})
    metrics = c.aggregator.flush()[:-1]

    assert len(metrics) == total_rates

    for metric in metrics:
        assert metric['metric'] in expected_rates
        assert len(metric['points']) == 1
        assert metric['host'] == HOSTNAME
        assert metric['type'] == GAUGE
        assert is_metric_expected(expected_rates, metric)
