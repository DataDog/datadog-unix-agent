# checks/corechecks/system/load/tests/test_load.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from aggregator import MetricsAggregator
from checks.corechecks.system.load.load import LoadCheck

GAUGE = 'gauge'

AIX_MOCK_LOAD = '  10:50AM   up 8 days,   2:48,  2 users,  load average: 1.19, 0.77, 0.85'


@mock.patch("psutil.cpu_count", return_value=2)
@mock.patch("os.getloadavg", return_value=(0.42, 0.43, 0.49))
def test_load(getloadavg, cpu_count):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LoadCheck("load", {}, {}, aggregator)
    c.check({})
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

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

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LoadCheck("load", {}, {}, aggregator)
    try:
        c.check({})
        assert False, "load check should have raised an error"
    except Exception as e:
        assert str(e) == "Cannot determine number of cores"

    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

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


@mock.patch("psutil.cpu_count", return_value=2)
@mock.patch("checks.corechecks.system.load.load.get_subprocess_output", return_value=(AIX_MOCK_LOAD, None, None))
@mock.patch("os.getloadavg", side_effect=AttributeError("'module' object has no attribute 'getloadavg')"))
def test_load_aix(getloadavg, get_subprocess_output, cpu_count):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LoadCheck("load", {}, {}, aggregator)
    c.check({})
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    expected_metrics = {
        'system.load.1': (GAUGE, 1.19),
        'system.load.5': (GAUGE, 0.77),
        'system.load.15': (GAUGE, 0.85),
        'system.load.norm.1': (GAUGE, 0.595),
        'system.load.norm.5': (GAUGE, 0.385),
        'system.load.norm.15': (GAUGE, 0.425),
    }

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']][0]
        assert metric['points'][0][1] == expected_metrics[metric['metric']][1]
