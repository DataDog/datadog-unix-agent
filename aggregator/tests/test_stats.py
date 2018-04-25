# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from aggregator.stats import AggregatorStats

def test_stats():
    # The min is not enabled by default
    stats = AggregatorStats()

    metric_stats = {
        'foo': 2,
        'bar': 5,
    }
    stats.set_last_flush_counts(mcount=4, ecount=2, sccount=1)
    stats.set_last_flush_metric_stats(metric_stats)

    flush_stats = stats.get_aggregator_stats()
    assert flush_stats['stats'] == metric_stats
    assert flush_stats['metric_count'] == 4
    assert flush_stats['event_count'] == 2
    assert flush_stats['service_check_count'] == 1

    # test we got a deepcopy
    metric_stats['foo'] += 10
    assert flush_stats['stats'] != metric_stats
    assert flush_stats['stats']['foo'] == 2

    # test flush counters
    mcount_1, ecount_1, sccount_1 = stats.get_last_flush_counts()
    assert mcount_1 == 4
    assert ecount_1 == 2
    assert sccount_1 == 1

    # update last flush counts
    stats.set_last_flush_counts(mcount=3, ecount=1, sccount=1)
    mcount_2, ecount_2, sccount_2 = stats.get_last_flush_counts()
    assert mcount_2 == 3
    assert ecount_2 == 1
    assert sccount_2 == 1

    # check totals
    mcount, ecount, sccount = stats.get_total_counts()
    assert mcount == mcount_1 + mcount_2
    assert ecount == ecount_1 + ecount_2
    assert sccount == sccount_1 + sccount_2
