# -*- coding: utf-8 -*-
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from aggregator.types import (
    MetricResolver,
    BucketMetricResolver,
)


class TestMetricResolver():

    def test_metric_resolver(self):
        resolver = MetricResolver()

        for mtype, typeclass in resolver.TYPES.iteritems():
            assert resolver[mtype] is not None
            assert resolver[mtype] == typeclass

        resolvable_types = ['c', 'g', 'h']
        resolver.set_resolvable_types(resolvable_types)
        for mtype in resolvable_types:
            assert resolver[mtype] is not None

        assert resolver['foo'] is None

    def test_bucket_metric_resolver(self):
        resolver = BucketMetricResolver()

        for mtype, typeclass in resolver.TYPES.iteritems():
            assert resolver[mtype] is not None
            assert resolver[mtype] == typeclass

        resolvable_types = ['c', 'g', 'h']
        resolver.set_resolvable_types(resolvable_types)
        for mtype in resolvable_types:
            assert resolver[mtype] is not None

        assert resolver['foo'] is None

        resolver.set_resolvable_types(None)
        unresolvable_types = ['ct', 'ct-c', '_dd-r']
        for mtype in unresolvable_types:
            assert resolver[mtype] is None
