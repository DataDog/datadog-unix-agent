# checks/corechecks/system/cpu/tests/test_cpu.py

import mock
from collections import namedtuple

from aggregator import MetricsAggregator
from checks.corechecks.system.cpu.cpu import CpuCheck


GAUGE = 'gauge'


@mock.patch("psutil.cpu_times_percent")
def test_cpu(mock_cpu_times):
    # Fake psutil scputimes
    scputimes = namedtuple('scputimes', ['user','system','idle','iowait'])

    mock_cpu_times.return_value = [
        scputimes(user=2.8, system=1.5, idle=94.7, iowait=1.0),
        scputimes(user=78.2, system=9.4, idle=10.3, iowait=2.1),
    ]

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = CpuCheck("cpu", {}, {}, aggregator)
    c.check({})

    metrics = c.aggregator.flush()[:-1]

    expected_metrics = {
        'system.cpu.user': {
            'type': GAUGE,
            'core:0': 2.8,
            'core:1': 78.2,
        },
        'system.cpu.system': {
            'type': GAUGE,
            'core:0': 1.5,
            'core:1': 9.4,
        },
        'system.cpu.idle': {
            'type': GAUGE,
            'core:0': 94.7,
            'core:1': 10.3,
        },
        'system.cpu.iowait': {
            'type': GAUGE,
            'core:0': 1.0,
            'core:1': 2.1,
        },
    }

    assert len(metrics) == len(expected_metrics)*2
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname

        metric_type = expected_metrics[metric['metric']]['type']
        assert metric['type'] == metric_type

        for tag in metric['tags']:
            stag = tag.decode('utf-8')
            if stag.startswith('core:'):
                expected_value = expected_metrics[metric['metric']][stag]
                assert metric['points'][0][1] == expected_value
