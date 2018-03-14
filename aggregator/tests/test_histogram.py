# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# project
from aggregator import MetricsAggregator
from aggregator.types import Histogram
from config import Config


class TestHistogram():
    def test_default(self):
        stats = MetricsAggregator('myhost')

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        assert len(metrics) == 5

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        assert sorted(value_by_type.keys()) == \
            ['95percentile', 'avg', 'count', 'max', 'median']

        assert value_by_type['max'] == 19
        assert value_by_type['median'] == 9
        assert value_by_type['avg'] == 9.5
        assert value_by_type['count'] == 20.0
        assert value_by_type['95percentile'] == 18

    def test_custom_single_percentile(self):
        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=[0.4]
        )

        assert stats.metric_config[Histogram]['percentiles'] == [0.40]

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        assert len(metrics) == 5

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        assert value_by_type['40percentile'] == 7

    def test_custom_multiple_percentile(self):
        conf = Config()
        conf.set('histogram_percentiles', [0.4, 0.65, 0.999])
        conf.validate()

        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=conf.get('histogram_percentiles')
        )

        assert stats.metric_config[Histogram]['percentiles'] == [0.4, 0.65, 0.99]

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        assert len(metrics) == 7

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        assert value_by_type['40percentile'] == 7
        assert value_by_type['65percentile'] == 12
        assert value_by_type['99percentile'] == 19

    def test_custom_invalid_percentile(self):
        conf = Config()
        conf.set('histogram_percentiles', [1.2342])
        conf.validate()

        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=conf.get('histogram_percentiles')
        )

        assert stats.metric_config[Histogram]['percentiles'] == []

    def test_custom_invalid_percentile2(self):
        conf = Config()
        conf.set('histogram_percentiles', ['aoeuoeu'])
        conf.validate()

        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=conf.get('histogram_percentiles')
        )

        assert stats.metric_config[Histogram]['percentiles'] == []

    def test_custom_invalid_percentile3skip(self):
        conf = Config()
        conf.set('histogram_percentiles', ['aoeuoeu', 2.23, 0.8, 23])
        conf.validate()

        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=conf.get('histogram_percentiles')
        )

        assert stats.metric_config[Histogram]['percentiles'] == [0.8]

    def test_custom_aggregate(self):
        conf = Config()
        conf.set('histogram_aggregates', ['median', 'max', 'sum'])
        conf.validate()

        stats = MetricsAggregator(
            'myhost',
            histogram_aggregates=conf.get('histogram_aggregates')
        )

        assert sorted(stats.metric_config[Histogram]['aggregates']) == \
            ['max', 'median', 'sum']

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        assert len(metrics) == 4

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        assert value_by_type['median'] == 9
        assert value_by_type['max'] == 19
        assert value_by_type['sum'] == 190
        assert value_by_type['95percentile'] == 18
