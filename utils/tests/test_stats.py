# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import pytest

from utils.stats import Stats


def test_stats():
    # The min is not enabled by default
    stats = Stats()

    metric_stats = {
        'foo': 2,
        'bar': 5,
    }

    # setters
    stats.set_stat('metrics', 4)
    stats.set_stat('events', 2)
    stats.set_stat('service_checks', 1)
    # totals
    stats.inc_stat('metrics_total', 4)
    stats.inc_stat('events_total', 2)
    stats.inc_stat('service_checks_total', 1)
    # info
    stats.set_info('metric_stats', metric_stats)

    stats_snapshot, info_snapshot = stats.snapshot()
    assert info_snapshot['metric_stats'] == metric_stats
    assert stats_snapshot['metrics'] == 4
    assert stats_snapshot['events'] == 2
    assert stats_snapshot['service_checks'] == 1
    assert stats_snapshot['metrics_total'] == 4
    assert stats_snapshot['events_total'] == 2
    assert stats_snapshot['service_checks_total'] == 1

    # test we got a deepcopy for stats
    stats.set_stat('metrics', 10)
    stats.inc_stat('metrics_total', 10)
    assert stats_snapshot != metric_stats
    assert stats_snapshot['metrics'] != stats.get_stat('metrics')

    # test we got a deepcopy for info
    metric_stats['bar'] += 1
    stats.set_info('metric_stats', metric_stats)
    assert info_snapshot != metric_stats
    assert info_snapshot['metric_stats']['foo'] == metric_stats['foo']
    assert info_snapshot['metric_stats']['bar'] != metric_stats['bar']

    # test for updated snapshots
    stats_snapshot, info_snapshot = stats.snapshot()
    assert stats_snapshot['metrics'] == 10
    assert stats_snapshot['metrics_total'] == 14
    assert info_snapshot['metric_stats']['foo'] == metric_stats['foo']
    assert info_snapshot['metric_stats']['bar'] == metric_stats['bar']

    # test strict get
    with pytest.raises(KeyError):
        stats.get_stat('nonexistent', strict=True)
    with pytest.raises(KeyError):
        stats.get_info('nonexistent', strict=True)

