# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from aggregator import MetricsAggregator

GAUGE = 'gauge'


@mock.patch("psutil.cpu_count", return_value=2)
@mock.patch("os.getloadavg", return_value=(0.42, 0.43, 0.49))
def test_load(getloadavg, cpu_count):
    from checks.corechecks.system import load

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = load.Load("load", {}, {}, aggregator)
    c.check({})
    metrics = c.aggregator.flush()

    expected_metrics = {
        'system.load.1': (GAUGE, 0.42),
        'system.load.5': (GAUGE, 0.43),
        'system.load.15': (GAUGE, 0.49),
        'system.load.norm.1': (GAUGE, 0.21),
        'system.load.norm.5': (GAUGE, 0.215),
        'system.load.norm.15': (GAUGE, 0.245),
    }

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]


@mock.patch("psutil.cpu_count", return_value=0)
@mock.patch("os.getloadavg", return_value=(0.42, 0.43, 0.49))
def test_load_no_cpu_count(getloadavg, cpu_count):
    from checks.corechecks.system import load

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = load.Load("load", {}, {}, aggregator)
    try:
        c.check({})
        assert 0, "load check should have raise an error"
    except Exception as e:
        assert str(e) == "Cannot determine number of cores"

    metrics = c.aggregator.flush()

    expected_metrics = {
        'system.load.1': (GAUGE, 0.42),
        'system.load.5': (GAUGE, 0.43),
        'system.load.15': (GAUGE, 0.49),
    }

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]
