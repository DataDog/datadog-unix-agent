# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
from time import time


log = logging.getLogger(__name__)


class Infinity(Exception):
    pass


class UnknownValue(Exception):
    pass


class MetricTypes(object):

    GAUGE = 'gauge'
    COUNTER = 'counter'
    RATE = 'rate'
    COUNT = 'count'

class Metric(object):
    """
    A base metric class that accepts points, slices them into time intervals
    and performs roll-ups within those intervals.
    """

    def sample(self, value, sample_rate, timestamp=None):
        """ Add a point to the given metric. """
        raise NotImplementedError()

    def flush(self, timestamp, interval):
        """ Flush all metrics up to the given timestamp. """
        raise NotImplementedError()


class Gauge(Metric):
    """ A metric that tracks a value at particular points in time. """

    def __init__(self, formatter, name, tags, hostname, extra_config=None):
        self.formatter = formatter
        self.name = name
        self.value = None
        self.tags = tags
        self.hostname = hostname
        self.last_sample_time = None
        self.timestamp = time()

    def sample(self, value, sample_rate, timestamp=None):
        self.value = value
        self.last_sample_time = time()
        self.timestamp = timestamp

    def flush(self, timestamp, interval):
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=self.timestamp or timestamp,
                value=self.value,
                tags=self.tags,
                hostname=self.hostname,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            )]
            self.value = None
            return res

        return []

class BucketGauge(Gauge):
    """ A metric that tracks a value at particular points in time.
    The difference beween this class and Gauge is that this class will
    report that gauge sample time as the time that Metric is flushed, as
    opposed to the time that the sample was collected.

    """

    def flush(self, timestamp, interval):
        if self.value is not None:
            res = [self.formatter(
                metric=self.name,
                timestamp=timestamp,
                value=self.value,
                tags=self.tags,
                hostname=self.hostname,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            )]
            self.value = None
            return res

        return []


class Count(Metric):
    """ A metric that tracks a count. """

    def __init__(self, formatter, name, tags, hostname, extra_config=None):
        self.formatter = formatter
        self.name = name
        self.value = None
        self.tags = tags
        self.hostname = hostname
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        self.value = (self.value or 0) + value
        self.last_sample_time = time()

    def flush(self, timestamp, interval):
        if self.value is None:
            return []
        try:
            return [self.formatter(
                metric=self.name,
                value=self.value,
                timestamp=timestamp,
                tags=self.tags,
                hostname=self.hostname,
                metric_type=MetricTypes.COUNT,
                interval=interval,
            )]
        finally:
            self.value = None

class MonotonicCount(Metric):

    def __init__(self, formatter, name, tags, hostname, extra_config=None):
        self.formatter = formatter
        self.name = name
        self.tags = tags
        self.hostname = hostname
        self.prev_counter = None
        self.curr_counter = None
        self.count = None
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        if self.curr_counter is None:
            self.curr_counter = value
        else:
            self.prev_counter = self.curr_counter
            self.curr_counter = value

        prev = self.prev_counter
        curr = self.curr_counter
        if prev is not None and curr is not None:
            self.count = (self.count or 0) + max(0, curr - prev)

        self.last_sample_time = time()

    def flush(self, timestamp, interval):
        if self.count is None:
            return []
        try:
            return [self.formatter(
                hostname=self.hostname,
                tags=self.tags,
                metric=self.name,
                value=self.count,
                timestamp=timestamp,
                metric_type=MetricTypes.COUNT,
                interval=interval
            )]
        finally:
            self.prev_counter = self.curr_counter
            self.curr_counter = None
            self.count = None


class Counter(Metric):
    """ A metric that tracks a counter value. """

    def __init__(self, formatter, name, tags, hostname, extra_config=None):
        self.formatter = formatter
        self.name = name
        self.value = 0
        self.tags = tags
        self.hostname = hostname
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        self.value += value * int(1 / sample_rate)
        self.last_sample_time = time()

    def flush(self, timestamp, interval):
        try:
            value = self.value / interval
            return [self.formatter(
                metric=self.name,
                value=value,
                timestamp=timestamp,
                tags=self.tags,
                hostname=self.hostname,
                metric_type=MetricTypes.RATE,
                interval=interval,
            )]
        finally:
            self.value = 0


DEFAULT_HISTOGRAM_AGGREGATES = ['max', 'median', 'avg', 'count']
DEFAULT_HISTOGRAM_PERCENTILES = [0.95]

class Histogram(Metric):
    """ A metric to track the distribution of a set of values. """

    def __init__(self, formatter, name, tags, hostname, extra_config=None):
        self.formatter = formatter
        self.name = name
        self.count = 0
        self.samples = []
        self.aggregates = extra_config['aggregates'] if\
            extra_config is not None and extra_config.get('aggregates') is not None\
            else DEFAULT_HISTOGRAM_AGGREGATES
        self.percentiles = extra_config['percentiles'] if\
            extra_config is not None and extra_config.get('percentiles') is not None\
            else DEFAULT_HISTOGRAM_PERCENTILES
        self.tags = tags
        self.hostname = hostname
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        self.count += int(1 / sample_rate)
        self.samples.append(value)
        self.last_sample_time = time()

    def flush(self, ts, interval):
        if not self.count:
            return []

        self.samples.sort()
        length = len(self.samples)

        min_ = self.samples[0]
        max_ = self.samples[-1]
        med = self.samples[int(round(length/2 - 1))]
        sum_ = sum(self.samples)
        avg = sum_ / float(length)

        aggregators = [
            ('min', min_, MetricTypes.GAUGE),
            ('max', max_, MetricTypes.GAUGE),
            ('median', med, MetricTypes.GAUGE),
            ('avg', avg, MetricTypes.GAUGE),
            ('sum', sum_, MetricTypes.GAUGE),
            ('count', self.count/interval, MetricTypes.RATE),
        ]

        metric_aggrs = [
            (agg_name, agg_func, m_type)
            for agg_name, agg_func, m_type in aggregators
            if agg_name in self.aggregates
        ]

        metrics = [self.formatter(
            hostname=self.hostname,
            tags=self.tags,
            metric='%s.%s' % (self.name, suffix),
            value=value,
            timestamp=ts,
            metric_type=metric_type,
            interval=interval) for suffix, value, metric_type in metric_aggrs
        ]

        for p in self.percentiles:
            val = self.samples[int(round(p * length - 1))]
            name = '%s.%spercentile' % (self.name, int(p * 100))
            metrics.append(self.formatter(
                hostname=self.hostname,
                tags=self.tags,
                metric=name,
                value=val,
                timestamp=ts,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            ))

        # Reset our state.
        self.samples = []
        self.count = 0

        return metrics


class Set(Metric):
    """ A metric to track the number of unique elements in a set. """

    def __init__(self, formatter, name, tags, hostname, extra_config=None):
        self.formatter = formatter
        self.name = name
        self.tags = tags
        self.hostname = hostname
        self.values = set()
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        self.values.add(value)
        self.last_sample_time = time()

    def flush(self, timestamp, interval):
        if not self.values:
            return []
        try:
            return [self.formatter(
                hostname=self.hostname,
                tags=self.tags,
                metric=self.name,
                value=len(self.values),
                timestamp=timestamp,
                metric_type=MetricTypes.GAUGE,
                interval=interval,
            )]
        finally:
            self.values = set()


class Rate(Metric):
    """ Track the rate of metrics over each flush interval """

    def __init__(self, formatter, name, tags, hostname, extra_config=None):
        self.formatter = formatter
        self.name = name
        self.tags = tags
        self.hostname = hostname
        self.samples = []
        self.last_sample_time = None

    def sample(self, value, sample_rate, timestamp=None):
        ts = time()
        self.samples.append((int(ts), value))
        self.last_sample_time = ts

    def _rate(self, sample1, sample2):
        interval = sample2[0] - sample1[0]
        if interval == 0:
            log.warn('Metric %s has an interval of 0. Not flushing.' % self.name)
            raise Infinity()

        delta = sample2[1] - sample1[1]
        if delta < 0:
            log.info('Metric %s has a rate < 0. Counter may have been Reset.' % self.name)
            raise UnknownValue()

        return (delta / float(interval))

    def flush(self, timestamp, interval):
        if len(self.samples) < 2:
            return []
        try:
            try:
                val = self._rate(self.samples[-2], self.samples[-1])
            except Exception:
                return []

            return [self.formatter(
                hostname=self.hostname,
                tags=self.tags,
                metric=self.name,
                value=val,
                timestamp=timestamp,
                metric_type=MetricTypes.GAUGE,
                interval=interval
            )]
        finally:
            self.samples = self.samples[-1:]


class TextualMetricTypes(object):
    COUNT = 'ct'
    COUNTER = 'c'
    GAUGE = 'g'
    HISTOGRAM = 'h'
    HISTOGRAM_TIMING = 'ms'
    MONOTONIC_COUNT = 'ct-c'
    RATE = '_dd-r'
    SET = 's'


class MetricResolver(object):
    """ Resolves types from textual form to Metric class """
    TYPES = {
        'ct': Count,
        'c': Counter,
        'g': Gauge,
        'h': Histogram,
        'ms': Histogram,
        'ct-c': MonotonicCount,
        '_dd-r': Rate,
        's': Set,
    }

    def __init__(self):
        self._acceptable_types = None

    def __getitem__(self, key):
        return self.get_class_from_type(key)

    def set_resolvable_types(self, types):
        """ Allows limiting the set of available types with an iterable """
        self._acceptable_types = types

    def get_class_from_type(self, mtype):
        """ Returns the resolved class or None """
        if self._acceptable_types and mtype not in self._acceptable_types:
            return None
        return self.TYPES.get(mtype)


class BucketMetricResolver(MetricResolver):
    TYPES = {
        'g': BucketGauge,
        'c': Counter,
        'h': Histogram,
        'ms': Histogram,
        's': Set,
    }
