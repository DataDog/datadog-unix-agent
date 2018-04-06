# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from aggregator import MetricsAggregator


@mock.patch("uptime.uptime", return_value=21)
def test_uptime_check(uptime):
    from checks.corechecks.system import uptime_check

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
