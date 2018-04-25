# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
from copy import deepcopy
from threading import Lock

log = logging.getLogger(__name__)


class AggregatorStats(object):
    def __init__(self):
        self._stats_mutex = Lock()
        self._last_flush_metric_stats = None

        self._last_flush_service_check_count = 0
        self._last_flush_metric_count = 0
        self._last_flush_event_count = 0
        self._total_service_check_count = 0
        self._total_metric_count = 0
        self._total_event_count = 0

    def get_last_flush_metric_stats(self):
        self._stats_mutex.acquire()
        try:
            stats = deepcopy(self._last_flush_metric_stats)
        finally:
            self._stats_mutex.release()

        return stats

    def set_last_flush_metric_stats(self, stats):
        self._stats_mutex.acquire()
        try:
            self._last_flush_metric_stats = deepcopy(stats)
        finally:
            self._stats_mutex.release()

        return stats

    def get_last_flush_counts(self):
        self._stats_mutex.acquire()
        try:
            mcount = self._last_flush_metric_count
            ecount = self._last_flush_event_count
            sccount = self._last_flush_service_check_count
        finally:
            self._stats_mutex.release()

        return mcount, ecount, sccount

    def get_total_counts(self):
        self._stats_mutex.acquire()
        try:
            mcount = self._total_metric_count
            ecount = self._total_event_count
            sccount = self._total_service_check_count
        finally:
            self._stats_mutex.release()

        return mcount, ecount, sccount

    def set_last_flush_counts(self, mcount=None, ecount=None, sccount=None):
        self._stats_mutex.acquire()
        try:
            if mcount is not None:
                self._last_flush_metric_count = mcount
                self._total_metric_count += mcount
            if ecount is not None:
                self._last_flush_event_count = ecount
                self._total_event_count += ecount
            if sccount is not None:
                self._last_flush_service_check_count = sccount
                self._total_service_check_count += sccount
        finally:
            self._stats_mutex.release()

    def get_aggregator_stats(self):
        self._stats_mutex.acquire()
        try:
            stats = deepcopy(self._last_flush_metric_stats)
            mcount = int(self._last_flush_metric_count)
            ecount = int(self._last_flush_event_count)
            sccount = int(self._last_flush_service_check_count)
        finally:
            self._stats_mutex.release()

        return {
            'stats': stats,
            'metric_pkt_count': mcount,
            'event_pkt_count': ecount,
            'service_check_pkt_count': sccount,
        }
