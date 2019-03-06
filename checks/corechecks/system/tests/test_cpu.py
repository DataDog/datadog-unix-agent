# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock
from collections import namedtuple

from aggregator import MetricsAggregator


GAUGE = 'gauge'
AIX_MOCK_IOSTAT = '''

System configuration: lcpu=8 drives=1 ent=0.40 paths=2 vdisks=2

tty:      tin         tout    avg-cpu: % user % sys % idle % iowait physc % entc
        0.0          0.8                0.0   0.0  100.0      0.5   0.0    0.1

Disks:         % tm_act     Kbps      tps    Kb_read   Kb_wrtn
hdisk11           0.0       0.8       0.1     919576  14296158
'''


@mock.patch("time.time")
@mock.patch("psutil.cpu_times")
@mock.patch("psutil.cpu_count", return_value=2)
@mock.patch("checks.corechecks.system.cpu.get_subprocess_output", return_value=(AIX_MOCK_IOSTAT, None, None))
def test_cpu_first_run(get_subprocess_output, cpu_count, cpu_times, time):
    from checks.corechecks.system import cpu

    # fake cputimes from psutil
    cputimes = namedtuple("cputimes",
            ["user", "nice", "system", "idle", "irq",
             "softirq", "steal", "guest", "guest_nice"])

    time.return_value = 0
    cpu_times.return_value = cputimes(
        user=16683.71,
        nice=6.04,
        system=1105424,
        idle=72991318,
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
    assert c.aggregator.flush()[:-1] == []  # we remove the datadog.agent.running metric

    time.return_value = 10
    cpu_times.return_value = cputimes(
        user=16683.74,
        nice=6.25,
        system=1105434,
        idle=72991321,
        irq=0.1,
        softirq=104.51,
        steal=0.0,
        guest=0.0,
        guest_nice=0.0)

    c.check({})
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric
    expected_metrics = {
        'system.cpu.system': (GAUGE, 51.5),
        'system.cpu.user': (GAUGE, 1.2),
        'system.cpu.idle': (GAUGE, 15.0),
        'system.cpu.stolen': (GAUGE, 0.0),
        'system.cpu.guest': (GAUGE, 0.0),
        'system.cpu.iowait': (GAUGE, 0.5),
        'system.cpu.physc': (GAUGE, 0.0),
        'system.cpu.entc': (GAUGE, 0.1),
    }

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]
