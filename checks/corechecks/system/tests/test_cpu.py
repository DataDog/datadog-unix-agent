# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock
from collections import namedtuple

from aggregator import MetricsAggregator


GAUGE = 'gauge'


@mock.patch("psutil.cpu_times")
@mock.patch("psutil.cpu_count", return_value=2)
def test_cpu_first_run(cpu_count, cpu_times):
    from checks.corechecks.system import cpu

    # fake cputimes from psutil
    cputimes = namedtuple("cputimes",
            ["user", "nice", "system", "idle", "irq",
             "softirq", "steal", "guest", "guest_nice"])

    cpu_times.return_value = cputimes(user=16683.71,
            nice=6.04,
            system=11054.24,
            idle=729913.18,
            irq=0.0,
            softirq=104.31,
            steal=0.0,
            guest=0.0,
            guest_nice=0.0)

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = cpu.Cpu("cpu", {}, {}, aggregator)
    c.check({})
    assert c.aggregator.flush() == []

    cpu_times.return_value = cputimes(user=16683.74,
            nice=6.25,
            system=11054.34,
            idle=729921.64,
            irq=0.1,
            softirq=104.51,
            steal=0.0,
            guest=0.0,
            guest_nice=0.0)

    c.check({})
    metrics = c.aggregator.flush()
    expected_metrics = {
        'system.cpu.system': (GAUGE, 0.2),
        'system.cpu.user': (GAUGE, 0.12),
        'system.cpu.idle': (GAUGE, 4.2300),
        'system.cpu.stolen': (GAUGE, 0.0),
        'system.cpu.guest': (GAUGE, 0.0),
    }

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]
