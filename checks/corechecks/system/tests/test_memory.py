# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock
from collections import namedtuple

from aggregator import MetricsAggregator


GAUGE = 'gauge'


@mock.patch("psutil.virtual_memory")
@mock.patch("psutil.swap_memory")
def test_memory_linux(swap_memory, virtual_memory):
    from checks.corechecks.system import memory

    svmem = namedtuple("svmem", ["total", "available", "percent", "used", "free",
                                 "active", "inactive", "buffers", "cached", "shared"])
    sswap = namedtuple("sswap", ["total", "used", "free", "percent", "sin", "sout"])

    virtual_memory.return_value = svmem(
        total=9177399296,
        available=5566582784,
        percent=39.3,
        used=2958319616,
        free=4841459712,
        active=1700761600,
        inactive=1062944768,
        buffers=68628480,
        cached=1308991488,
        shared=500330496)
    swap_memory.return_value = sswap(
        total=10485755904,
        used=1024,
        free=10485754880,
        percent=1.0,
        sin=0,
        sout=0)

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = memory.Memory("memory", {}, {}, aggregator)
    c.check({})

    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    expected_metrics = {
        'system.mem.total': (GAUGE, 8752),
        'system.mem.free': (GAUGE, 4617),
        'system.mem.used': (GAUGE, 4135),
        'system.mem.usable': (GAUGE, 5309),
        'system.mem.pct_usable': (GAUGE, 0.6066),
        'system.swap.total': (GAUGE, 10000),
        'system.swap.free': (GAUGE, 10000),
        'system.swap.used': (GAUGE, 0),
        'system.swap.pct_free': (GAUGE, 1),
    }

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]
