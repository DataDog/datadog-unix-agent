# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
from time import time
from collections import defaultdict, Hashable

# project
from .types import (
    Counter,
    Histogram,
    MetricResolver,
    BucketMetricResolver,
)

from config.default import DEFAULT_RECENT_POINT_THRESHOLD
from .formatters import api_formatter
from. stats import AggregatorStats


log = logging.getLogger(__name__)

UNKNOWN_SOURCE = 'unknown'


class Aggregator(object):
    """
    Abstract metric aggregator class.
    """
    # Types of metrics that allow strings
    ALLOW_STRINGS = ['s', ]
    # Types that are not implemented and ignored
    IGNORE_TYPES = ['d', ]

    def __init__(self, hostname, interval=1.0, expiry_seconds=300,
                 formatter=None, recent_point_threshold=None,
                 histogram_aggregates=None, histogram_percentiles=None,
                 utf8_decoding=False):
        # TODO(jaime): add support for event, service_check sources
        self.events = []
        self.service_checks = []

        self.stats = AggregatorStats()
        # TODO(jaime): we can probably kill total counts
        self.total_count = 0
        self.count = 0
        self.event_count = 0
        self.service_check_count = 0
        self.hostname = hostname
        self.expiry_seconds = expiry_seconds
        self.formatter = formatter or api_formatter
        self.interval = float(interval)

        recent_point_threshold = recent_point_threshold or DEFAULT_RECENT_POINT_THRESHOLD
        self.recent_point_threshold = int(recent_point_threshold)
        self.num_discarded_old_points = 0

        # Additional config passed when instantiating metric configs
        self.metric_config = {
            Histogram: {
                'aggregates': histogram_aggregates,
                'percentiles': histogram_percentiles
            }
        }

        self.utf8_decoding = utf8_decoding

    def deduplicate_tags(self, tags):
        return sorted(set(tags))

    def packets_per_second(self, interval):
        if interval == 0:
            return 0
        return round(float(self.count)/interval, 2)

    def parse_metric_packet(self, packet):
        """
        Schema of a dogstatsd packet:
        <name>:<value>|<metric_type>|@<sample_rate>|#<tag1_name>:<tag1_value>,<tag2_name>:<tag2_value>:<value>|<metric_type>...
        """
        parsed_packets = []
        name_and_metadata = packet.split(':', 1)

        if len(name_and_metadata) != 2:
            raise Exception(u'Unparseable metric packet: %s' % packet)

        name = name_and_metadata[0]
        broken_split = name_and_metadata[1].split(':')
        data = []
        partial_datum = None
        for token in broken_split:
            # We need to fix the tag groups that got broken by the : split
            if partial_datum is None:
                partial_datum = token
            elif "|" not in token:
                partial_datum += ":" + token
            else:
                data.append(partial_datum)
                partial_datum = token
        data.append(partial_datum)

        for datum in data:
            value_and_metadata = datum.split('|')

            if len(value_and_metadata) < 2:
                raise Exception(u'Unparseable metric packet: %s' % packet)

            # Submit the metric
            raw_value = value_and_metadata[0]
            metric_type = value_and_metadata[1]

            if metric_type in self.ALLOW_STRINGS:
                value = raw_value
            elif len(metric_type) > 0 and metric_type[0] in self.IGNORE_TYPES:
                continue
            else:
                # Try to cast as an int first to avoid precision issues, then as a
                # float.
                try:
                    value = int(raw_value)
                except ValueError:
                    try:
                        value = float(raw_value)
                    except ValueError:
                        # Otherwise, raise an error saying it must be a number
                        raise Exception(u'Metric value must be a number: %s, %s' % (name, raw_value))

            # Parse the optional values - sample rate & tags.
            sample_rate = 1
            tags = None
            try:
                for m in value_and_metadata[2:]:
                    # Parse the sample rate
                    if m[0] == '@':
                        sample_rate = float(m[1:])
                        # in case it's in a bad state
                        sample_rate = 1 if sample_rate < 0 or sample_rate > 1 else sample_rate
                    elif m[0] == '#':
                        tags = tuple(sorted(m[1:].split(',')))
            except IndexError:
                log.warning(u'Incorrect metric metadata: metric_name:%s, metadata:%s',
                            name, u' '.join(value_and_metadata[2:]))

            parsed_packets.append((name, value, metric_type, tags, sample_rate))

        return parsed_packets

    def _unescape_sc_content(self, string):
        return string.replace('\\n', '\n').replace('m\:', 'm:')

    def _unescape_event_text(self, string):
        return string.replace('\\n', '\n')

    def parse_event_packet(self, packet):
        try:
            name_and_metadata = packet.split(':', 1)
            if len(name_and_metadata) != 2:
                raise Exception(u'Unparseable event packet: %s' % packet)
            # Event syntax:
            # _e{5,4}:title|body|meta
            name = name_and_metadata[0]
            metadata = name_and_metadata[1]
            title_length, text_length = name.split(',')
            title_length = int(title_length[3:])
            text_length = int(text_length[:-1])

            event = {
                'title': metadata[:title_length],
                'text': self._unescape_event_text(metadata[title_length+1:title_length+text_length+1])
            }
            meta = metadata[title_length+text_length+1:]
            for m in meta.split('|')[1:]:
                if m[0] == u't':
                    event['alert_type'] = m[2:]
                elif m[0] == u'k':
                    event['aggregation_key'] = m[2:]
                elif m[0] == u's':
                    event['source_type_name'] = m[2:]
                elif m[0] == u'd':
                    event['date_happened'] = int(m[2:])
                elif m[0] == u'p':
                    event['priority'] = m[2:]
                elif m[0] == u'h':
                    event['hostname'] = m[2:]
                elif m[0] == u'#':
                    event['tags'] = self.deduplicate_tags(m[1:].split(u','))
            return event
        except (IndexError, ValueError):
            raise Exception(u'Unparseable event packet: %s' % packet)

    def parse_sc_packet(self, packet):
        try:
            _, data_and_metadata = packet.split('|', 1)
            # Service check syntax:
            # _sc|check_name|status|meta
            if data_and_metadata.count('|') == 1:
                # Case with no metadata
                check_name, status = data_and_metadata.split('|')
                metadata = ''
            else:
                check_name, status, metadata = data_and_metadata.split('|', 2)

            service_check = {
                'check_name': check_name,
                'status': int(status)
            }

            message_delimiter = 'm:' if metadata.startswith('m:') else '|m:'
            if message_delimiter in metadata:
                meta, message = metadata.rsplit(message_delimiter, 1)
                service_check['message'] = self._unescape_sc_content(message)
            else:
                meta = metadata

            if not meta:
                return service_check

            meta = unicode(meta)
            for m in meta.split('|'):
                if m[0] == u'd':
                    service_check['timestamp'] = float(m[2:])
                elif m[0] == u'h':
                    service_check['hostname'] = m[2:]
                elif m[0] == u'#':
                    service_check['tags'] = self.deduplicate_tags(m[1:].split(u','))

            return service_check

        except (IndexError, ValueError):
            raise Exception(u'Unparseable service check packet: %s' % packet)

    def submit_packets(self, packets):
        # We should probably consider that packets are always encoded
        # in utf8, but decoding all packets has an perf overhead of 7%
        # So we let the user decide if we wants utf8 by default
        # Keep a very conservative approach anyhow
        # Clients MUST always send UTF-8 encoded content
        if self.utf8_decoding:
            packets = unicode(packets, 'utf-8', errors='replace')

        for packet in packets.splitlines():
            if not packet.strip():
                continue

            if packet.startswith('_e'):
                event = self.parse_event_packet(packet)
                self.event(**event)
                self.event_count += 1
            elif packet.startswith('_sc'):
                service_check = self.parse_sc_packet(packet)
                self.service_check(**service_check)
                self.service_check_count += 1
            else:
                parsed_packets = self.parse_metric_packet(packet)
                self.count += 1
                for name, value, mtype, tags, sample_rate in parsed_packets:
                    hostname, tags = self._extract_magic_tags(tags)
                    self.submit_metric(name, value, mtype, tags=tags,
                                       hostname=hostname, sample_rate=sample_rate)

    def _extract_magic_tags(self, tags):
        """Magic tags (host) override metric hostname attributes"""
        hostname = None
        # This implementation avoid list operations for the common case
        if tags:
            tags_to_remove = []
            for tag in tags:
                if tag.startswith('host:'):
                    hostname = tag[5:]
                    tags_to_remove.append(tag)
            if tags_to_remove:
                # tags is a tuple already sorted, we convert it into a list to pop elements
                tags = list(tags)
                for tag in tags_to_remove:
                    tags.remove(tag)
                tags = tuple(tags) or None
        return hostname, tags

    def submit_metric(self, name, value, mtype, tags=None, hostname=None,
                      timestamp=None, sample_rate=1):
        """ Add a metric to be aggregated """
        raise NotImplementedError()

    def event(self, title, text, date_happened=None, alert_type=None, aggregation_key=None,
              source_type_name=None, priority=None, tags=None, hostname=None):
        event = {
            'msg_title': title,
            'msg_text': text,
        }
        if date_happened is not None:
            event['timestamp'] = date_happened
        else:
            event['timestamp'] = int(time())
        if alert_type is not None:
            event['alert_type'] = alert_type
        if aggregation_key is not None:
            event['aggregation_key'] = aggregation_key
        if source_type_name is not None:
            event['source_type_name'] = source_type_name
        if priority is not None:
            event['priority'] = priority
        if tags is not None:
            event['tags'] = self.deduplicate_tags(tags)
        if hostname is not None:
            event['host'] = hostname
        else:
            event['host'] = self.hostname

        self.events.append(event)

    def service_check(self, check_name, status, tags=None, timestamp=None,
                      hostname=None, message=None):
        service_check = {
            'check': check_name,
            'status': status,
            'timestamp': timestamp or int(time())
        }
        if tags is not None:
            service_check['tags'] = self.deduplicate_tags(tags)

        if hostname is not None:
            service_check['host_name'] = hostname
        else:
            service_check['host_name'] = self.hostname
        if message is not None:
            service_check['message'] = message

        self.service_checks.append(service_check)

    def flush(self):
        """ Flush aggregated metrics """
        raise NotImplementedError()

    def flush_events(self):
        events = self.events
        self.events = []

        self.stats.set_last_flush_counts(ecount=self.event_count)
        self.total_count += self.event_count
        self.event_count = 0

        log.debug("Received %d events since last flush" % len(events))

        return events

    def flush_service_checks(self):
        service_checks = self.service_checks
        self.service_checks = []

        self.stats.set_last_flush_counts(sccount=self.service_check_count)
        self.total_count += self.service_check_count
        self.service_check_count = 0

        log.debug("Received {0} service check runs since last flush".format(len(service_checks)))

        return service_checks

    def send_packet_count(self, metric_name):
        self.submit_metric(metric_name, self.count, 'g')


class MetricsBucketAggregator(Aggregator):
    """
    A metric aggregator class.
    This class aggregates metrics by context into time buckets (1s).
    This is required by dogstatsd where there may be a continuous flow of
    incoming metrics and thus no implicit check-run assumptions can be made.

    Metric types supported by this aggregator: Gauge(BucketGauge), Counter,
                                               Histogram, Set
    """

    def __init__(self, hostname, interval=1.0, expiry_seconds=300,
                 formatter=None, recent_point_threshold=None,
                 histogram_aggregates=None, histogram_percentiles=None,
                 utf8_decoding=False):
        super(MetricsBucketAggregator, self).__init__(
            hostname,
            interval,
            expiry_seconds,
            formatter,
            recent_point_threshold,
            histogram_aggregates,
            histogram_percentiles,
            utf8_decoding
        )
        self.metric_by_bucket = {}
        self.last_sample_time_by_context = {}
        self.current_bucket = None
        self.current_mbc = {}
        self.last_flush_cutoff_time = 0
        self.metric_type_to_class = BucketMetricResolver()

    def calculate_bucket_start(self, timestamp):
        return timestamp - (timestamp % self.interval)

    def submit_metric(self, name, value, mtype, tags=None, hostname=None,
                      timestamp=None, sample_rate=1):
        # Avoid calling extra functions to dedupe tags if there are none
        # Note: if you change the way that context is created, please also
        # change create_empty_metrics, which counts on this order

        # Keep hostname with empty string to unset it
        hostname = hostname if hostname is not None else self.hostname

        if tags is None:
            context = (name, tuple(), hostname)
        else:
            tags = tuple(self.deduplicate_tags(tags))
            context = (name, tags, hostname)

        cur_time = time()
        # Check to make sure that the timestamp that is passed in (if any) is
        # not older than recent_point_threshold.  If so, discard the point.
        if timestamp is not None and cur_time - int(timestamp) > self.recent_point_threshold:
            log.debug("Discarding %s - ts = %s , current ts = %s " % (name, timestamp, cur_time))
            self.num_discarded_old_points += 1
        else:
            timestamp = timestamp or cur_time
            # Keep track of the buckets using the timestamp at the start time of the bucket
            bucket_start_timestamp = self.calculate_bucket_start(timestamp)
            if bucket_start_timestamp == self.current_bucket:
                metric_by_context = self.current_mbc
            else:
                if bucket_start_timestamp not in self.metric_by_bucket:
                    self.metric_by_bucket[bucket_start_timestamp] = {}
                metric_by_context = self.metric_by_bucket[bucket_start_timestamp]
                self.current_bucket = bucket_start_timestamp
                self.current_mbc = metric_by_context

            if context not in metric_by_context:
                metric_class = self.metric_type_to_class[mtype]
                metric_by_context[context] = \
                    metric_class(self.formatter, name, tags,
                                 hostname, self.metric_config.get(metric_class))

            metric_by_context[context].sample(value, sample_rate, timestamp)

    def create_empty_metrics(self, sample_time_by_context, expiry_timestamp, flush_timestamp, metrics):
        # Even if no data is submitted, Counters keep reporting "0" for expiry_seconds.  The other Metrics
        #  (Set, Gauge, Histogram) do not report if no data is submitted
        for context, last_sample_time in sample_time_by_context.items():
            if last_sample_time < expiry_timestamp:
                log.debug("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                self.last_sample_time_by_context.pop(context, None)
            else:
                # The expiration currently only applies to Counters
                # This counts on the ordering of the context created in submit_metric not changing
                metric = Counter(self.formatter, context[0], context[1], context[2])
                metrics += metric.flush(flush_timestamp, self.interval)

    def flush(self):
        cur_time = time()
        flush_cutoff_time = self.calculate_bucket_start(cur_time)
        expiry_timestamp = cur_time - self.expiry_seconds

        metrics = []

        if self.metric_by_bucket:
            # We want to process these in order so that we can check for and expired metrics and
            #  re-create non-expired metrics.  We also mutate self.metric_by_bucket.
            for bucket_start_timestamp in sorted(self.metric_by_bucket.keys()):
                metric_by_context = self.metric_by_bucket[bucket_start_timestamp]
                if bucket_start_timestamp < flush_cutoff_time:
                    not_sampled_in_this_bucket = self.last_sample_time_by_context.copy()
                    # We mutate this dictionary while iterating so don't use an iterator.
                    for context, metric in metric_by_context.items():
                        if metric.last_sample_time < expiry_timestamp:
                            # This should never happen
                            log.warning("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                            not_sampled_in_this_bucket.pop(context, None)
                            self.last_sample_time_by_context.pop(context, None)
                        else:
                            metrics += metric.flush(bucket_start_timestamp, self.interval)
                            if isinstance(metric, Counter):
                                self.last_sample_time_by_context[context] = metric.last_sample_time
                                not_sampled_in_this_bucket.pop(context, None)
                    # We need to account for Metrics that have not expired and were not flushed for this bucket
                    self.create_empty_metrics(not_sampled_in_this_bucket, expiry_timestamp, bucket_start_timestamp, metrics)

                    del self.metric_by_bucket[bucket_start_timestamp]
        else:
            # Even if there are no metrics in this flush, there may be some non-expired counters
            #  We should only create these non-expired metrics if we've passed an interval since the last flush
            if flush_cutoff_time >= self.last_flush_cutoff_time + self.interval:
                self.create_empty_metrics(self.last_sample_time_by_context.copy(), expiry_timestamp,
                                          flush_cutoff_time-self.interval, metrics)

        # Log a warning regarding metrics with old timestamps being submitted
        if self.num_discarded_old_points > 0:
            log.warn('%s points were discarded as a result of having an old timestamp' % self.num_discarded_old_points)
            self.num_discarded_old_points = 0

        # Save some stats.
        log.debug("received %s payloads since last flush" % self.count)
        self.stats.set_last_flush_counts(mcount=self.count)
        self.total_count += self.count
        self.count = 0
        self.current_bucket = None
        self.current_mbc = {}
        self.last_flush_cutoff_time = flush_cutoff_time
        return metrics


class MetricsAggregator(Aggregator):
    """
    A metric aggregator class.
    This class aggregates metrics by context.
    This is the default aggregator used by the agent collector.

    Metric types supported by this aggregator: Gauge, Count, MonotonicCount,
                                               Counter, Histogram, Set, Rate
    """

    def __init__(self, hostname, interval=1.0, expiry_seconds=300,
                 formatter=None, recent_point_threshold=None,
                 histogram_aggregates=None, histogram_percentiles=None,
                 utf8_decoding=False):
        super(MetricsAggregator, self).__init__(
            hostname,
            interval,
            expiry_seconds,
            formatter,
            recent_point_threshold,
            histogram_aggregates,
            histogram_percentiles,
            utf8_decoding
        )
        self.sources = defaultdict(set)
        self.metrics = {}
        self.metric_type_to_class = MetricResolver()

    def submit_metric(self, name, value, mtype, tags=None, hostname=None,
                      timestamp=None, sample_rate=1, source=None):
        # Avoid calling extra functions to dedupe tags if there are none

        # Keep hostname with empty string to unset it
        hostname = hostname if hostname is not None else self.hostname

        source = UNKNOWN_SOURCE if not source else source
        if not isinstance(source, Hashable):
            source = UNKNOWN_SOURCE

        if tags is None:
            context = (name, tuple(), hostname)
        else:
            tags = tuple(self.deduplicate_tags(tags))
            context = (name, tags, hostname)

        if context not in self.metrics:
            metric_class = self.metric_type_to_class[mtype]
            self.metrics[context] = \
                metric_class(self.formatter, name, tags,
                             hostname, self.metric_config.get(metric_class))

        if context not in self.sources[source]:
            self.sources[source].add(context)

        cur_time = time()
        if timestamp is not None and cur_time - int(timestamp) > self.recent_point_threshold:
            log.debug("Discarding %s - ts = %s , current ts = %s " % (name, timestamp, cur_time))
            self.num_discarded_old_points += 1
        else:
            self.metrics[context].sample(value, sample_rate, timestamp)

    def gauge(self, name, value, tags=None, hostname=None, timestamp=None, source=None):
        self.submit_metric(name, value, 'g', tags, hostname, timestamp, source)

    def increment(self, name, value=1, tags=None, hostname=None, source=None):
        self.submit_metric(name, value, 'c', tags, hostname, source)

    def decrement(self, name, value=-1, tags=None, hostname=None, source=None):
        self.submit_metric(name, value, 'c', tags, hostname, source)

    def rate(self, name, value, tags=None, hostname=None, source=None):
        self.submit_metric(name, value, '_dd-r', tags, hostname, source)

    def submit_count(self, name, value, tags=None, hostname=None, source=None):
        self.submit_metric(name, value, 'ct', tags, hostname, source)

    def count_from_counter(self, name, value, tags=None,
                           hostname=None, source=None):
        self.submit_metric(name, value, 'ct-c', tags, hostname, source)

    def histogram(self, name, value, tags=None, hostname=None, source=None):
        self.submit_metric(name, value, 'h', tags, hostname, source)

    def set(self, name, value, tags=None, hostname=None, source=None):
        self.submit_metric(name, value, 's', tags, hostname, source)

    def flush(self):
        timestamp = time()
        expiry_timestamp = timestamp - self.expiry_seconds

        # Flush points and remove expired metrics. We mutate this dictionary
        # while iterating so don't use an iterator.
        metrics = []
        for context, metric in self.metrics.items():
            if metric.last_sample_time < expiry_timestamp:
                log.debug("%s hasn't been submitted in %ss. Expiring." % (context, self.expiry_seconds))
                del self.metrics[context]
            else:
                metrics += metric.flush(timestamp, self.interval)

        # Log a warning regarding metrics with old timestamps being submitted
        if self.num_discarded_old_points > 0:
            log.warn('%s points were discarded as a result of having an old timestamp' % self.num_discarded_old_points)
            self.num_discarded_old_points = 0

        # generate some stats
        stats_by_source = {}
        for source, contexts in self.sources.iteritems():
            stats_by_source[source] = len(contexts)

        # Save some stats.
        self.stats.set_last_flush_metric_stats(stats_by_source)
        self.stats.set_last_flush_counts(mcount=self.count)
        log.debug("received %s payloads since last flush" % self.count)

        self.count = 0
        self.total_count += self.count

        return metrics
