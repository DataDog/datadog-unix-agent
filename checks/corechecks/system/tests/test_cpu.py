# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock
from collections import namedtuple

from aggregator import MetricsAggregator

GAUGE = 'gauge'


@mock.patch("psutil.cpu_times_percent")
def test_cpu_first_run(cpu_times_percent):
    from checks.corechecks.system import cpu

    # fake cputimes from psutil
    scputimes = namedtuple('scputimes', ['user','system', 'idle', 'iowait'])

    cpu_times_percent.return_value = [
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

    c = cpu.Cpu("cpu", {}, {}, aggregator)
    c.check({})
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric
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
            'core:0': 2.1,
        },
    }

    assert len(metrics) == len(expected_metrics)*2  # 2 values per metric
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']]['type']
        for tag in metric['tags']:
            stag = str(tag)
            if stag.startswith('core'):
                assert metric['points'][0][1] == expected_metrics[metric['metric']][stag]
