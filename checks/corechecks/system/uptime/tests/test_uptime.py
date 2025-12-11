# checks/corechecks/system/uptime/tests/test_uptime.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from aggregator import MetricsAggregator
from checks.corechecks.system.uptime.uptime import UptimeCheck


@mock.patch("uptime.uptime", return_value=21)
def test_uptime_check(mock_uptime):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    u = UptimeCheck("uptime", {}, {}, aggregator)
    u.check({})

    expected_metrics = {
        'system.uptime': ('gauge', 21),
    }
    metrics = u.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    assert len(metrics) != 0
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]


@mock.patch("uptime.uptime", return_value=None)
@mock.patch("checks.corechecks.system.uptime.uptime.get_subprocess_output",
            return_value=(' 8-00:56:09', None, None))
def test_uptime_check_subprocess(mock_subprocess, mock_uptime):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    u = UptimeCheck("uptime", {}, {}, aggregator)
    u.check({})

    # 8 days = 8*86400 = 691200
    # 56 minutes = 3360
    # 9 sec
    expected_total = 691200 + 3360 + 9  # 694569

    expected_metrics = {
        'system.uptime': ('gauge', expected_total),
    }
    metrics = u.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    assert len(metrics) != 0
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]


@mock.patch("uptime.uptime", return_value=None)
@mock.patch("checks.corechecks.system.uptime.uptime.get_subprocess_output",
            return_value=('   00:56:09', None, None))
def test_uptime_check_subprocess_nodays(mock_subprocess, mock_uptime):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    u = UptimeCheck("uptime", {}, {}, aggregator)
    u.check({})

    # 56 min = 3360 sec
    # 9 sec
    expected_total = 3360 + 9  # 3369

    expected_metrics = {
        'system.uptime': ('gauge', expected_total),
    }
    metrics = u.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    assert len(metrics) != 0
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]
