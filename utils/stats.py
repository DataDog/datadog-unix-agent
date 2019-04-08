# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
from collections import Counter
from copy import deepcopy
from threading import Lock

log = logging.getLogger(__name__)


class Stats(object):
    def __init__(self):
        self._stats_mutex = Lock()
        self._stats = Counter()
        self._info = {}

    def lock_acquire(self):
        self._stats_mutex.acquire()

    def lock_release(self):
        self._stats_mutex.release()

    def set_info(self, key, value):
        self.lock_acquire()
        try:
            self.set_info_unsafe(key, value)
        finally:
            self.lock_release()

    def get_info(self, key, strict=False):
        self.lock_acquire()
        try:
            return self.get_info_unsafe(key, strict)
        finally:
            self.lock_release()

    def set_info_unsafe(self, key, value):
        self._info[key] = value

    def get_info_unsafe(self, key, strict=False):
        if strict and key not in self._info:
            raise KeyError()

        return self._info[key]

    def inc_stat(self, key, value):
        self._stats_mutex.acquire()
        try:
            self._stats[key] += value
        finally:
            self._stats_mutex.release()

    def set_stat(self, key, value):
        self._stats_mutex.acquire()
        try:
            self._stats[key] = value
        finally:
            self._stats_mutex.release()

    def get_stat(self, key, strict=False):
        self._stats_mutex.acquire()
        try:
            if strict and key not in self._stats:
                raise KeyError()

            return self._stats[key]
        finally:
            self._stats_mutex.release()

    def snapshot(self):
        self._stats_mutex.acquire()
        try:
            stats = deepcopy(self._stats)
            info = deepcopy(self._info)
        finally:
            self._stats_mutex.release()

        return stats, info
