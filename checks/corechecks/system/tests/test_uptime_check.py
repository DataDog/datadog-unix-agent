# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from checks.corechecks.system import uptime_check
from aggregator import MetricsAggregator


@mock.patch("uptime.uptime", return_value=21)
def test_uptime_check(uptime):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    u = uptime_check.UptimeCheck("uptime", {}, {}, aggregator)
    u.check({})

    expected_metrics = {
        'system.uptime': ('gauge', 21),
    }
    metrics = u.aggregator.flush()

    assert len(metrics) != 0
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]


@mock.patch("uptime.uptime", return_value=None)
@mock.patch("checks.corechecks.system.uptime_check.get_subprocess_output", return_value=(' 8-00:56:09', None, None))
def test_uptime_check_subprocess(uptime, subprocess):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    u = uptime_check.UptimeCheck("uptime", {}, {}, aggregator)
    u.check({})

    expected_metrics = {
        'system.uptime': ('gauge', 694569.0),
    }
    metrics = u.aggregator.flush()

    assert len(metrics) != 0
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]
