# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from aggregator import MetricsAggregator

from .conftest import (
    AIX_LPARSTATS_HYPERVISOR,
    AIX_LPARSTATS_MEMORY_ENTITLEMENTS,
)


GAUGE = 'gauge'


def collect_column(input, row_idx):
    collected = []
    for row in input:
        name = filter(None, row.split(' '))[row_idx]
        collected.append(name)

    return collected

def test_memory(subprocess_patch):
    # defer import to test to avoid breaking get_subprocess_output
    # patching.
    from datadog_checks.lparstats import LPARStats

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LPARStats("lparstats", {}, {}, aggregator)
    c.collect_memory(page_stats=False)
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    # NOTE: iomu, iomf, iohwm unavailable
    expected_metrics = [
        'system.lpar.memory.physb',
        'system.lpar.memory.hpi',
        'system.lpar.memory.hpit',
        'system.lpar.memory.pmem',
        'system.lpar.memory.iomin',
        'system.lpar.memory.iomaf',
        'system.lpar.memory.entc',
        'system.lpar.memory.vcsw',
    ]

    # # we subtract two - one for /proc, and one for the heading
    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics


def test_memory_page(subprocess_patch):
    # defer import to test to avoid breaking get_subprocess_output
    # patching.
    from datadog_checks.lparstats import LPARStats

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LPARStats("lparstats", {}, {}, aggregator)
    c.collect_memory(page_stats=True)
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    # NOTE: iomf unavailable
    expected_metrics = [
        'system.lpar.memory.physb',
        'system.lpar.memory.hpi',
        'system.lpar.memory.hpit',
        'system.lpar.memory.pmem',
        'system.lpar.memory.iomu',
        'system.lpar.memory.iomin',
        'system.lpar.memory.iohwm',
        'system.lpar.memory.iomaf',
        'system.lpar.memory.pgcol',
        'system.lpar.memory.mpgcol',
        'system.lpar.memory.ccol',
        'system.lpar.memory.entc',
        'system.lpar.memory.vcsw',
    ]

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics


def test_memory_entitlements(subprocess_patch):
    # defer import to test to avoid breaking get_subprocess_output
    # patching.
    from datadog_checks.lparstats import LPARStats

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LPARStats("lparstats", {}, {}, aggregator)
    c.collect_memory_entitlements()
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    expected_metrics = [
        'system.lpar.memory.entitlement.iomin',
        'system.lpar.memory.entitlement.iodes',
        'system.lpar.memory.entitlement.iomu',
        'system.lpar.memory.entitlement.iores',
        'system.lpar.memory.entitlement.iohwm',
        'system.lpar.memory.entitlement.iomaf',
    ]

    # compile entitlements from mock output
    output = filter(None, AIX_LPARSTATS_MEMORY_ENTITLEMENTS.splitlines())
    output = output[c.MEMORY_ENTITLEMENTS_START_IDX + 1:]
    entitlements = collect_column(output, 0)

    assert len(metrics) == (len(expected_metrics) * len(entitlements))
    for metric in metrics:
        for tag in metric['tags']:
            if 'iompn' in tag:
                assert tag.split(':')[1] in entitlements


def test_hypervisor(subprocess_patch):
    # defer import to test to avoid breaking get_subprocess_output
    # patching.
    from datadog_checks.lparstats import LPARStats

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LPARStats("lparstats", {}, {}, aggregator)
    c.collect_hypervisor()
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    # compile hypervisor calls from mock output
    output = filter(None, AIX_LPARSTATS_HYPERVISOR.splitlines())
    output = output[c.HYPERVISOR_METRICS_START_IDX:-1]
    calls = collect_column(output, 0)

    assert len(metrics) == (len(c.HYPERVISOR_IDX_METRIC_MAP) * len(calls))
    for metric in metrics:
        assert metric['metric'] in c.HYPERVISOR_IDX_METRIC_MAP.values()
        for tag in metric['tags']:
            if 'call' in tag:
                assert tag.split(':')[1] in calls


def test_spurr(subprocess_patch):
    # defer import to test to avoid breaking get_subprocess_output
    # patching.
    from datadog_checks.lparstats import LPARStats

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = LPARStats("lparstats", {}, {}, aggregator)
    c.collect_spurr()
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    expected_metrics = [
        'system.lpar.spurr.user',
        'system.lpar.spurr.sys',
        'system.lpar.spurr.wait',
        'system.lpar.spurr.idle',
        'system.lpar.spurr.user.norm',
        'system.lpar.spurr.sys.norm',
        'system.lpar.spurr.wait.norm',
        'system.lpar.spurr.idle.norm',
        'system.lpar.spurr.user.pct',
        'system.lpar.spurr.sys.pct',
        'system.lpar.spurr.wait.pct',
        'system.lpar.spurr.idle.pct',
        'system.lpar.spurr.user.norm.pct',
        'system.lpar.spurr.sys.norm.pct',
        'system.lpar.spurr.wait.norm.pct',
        'system.lpar.spurr.idle.norm.pct',
    ]

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
