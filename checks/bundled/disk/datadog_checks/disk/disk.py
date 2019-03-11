# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import os

# 3p
import psutil

# project
from utils.util import _is_affirmative
from checks import AgentCheck


class Disk(AgentCheck):
    METRIC_DISK = 'system.disk.{}'
    USAGE_ATTRS = ['total', 'used', 'free']
    IO_ATTRS = ['read_count', 'write_count', 'read_bytes', 'write_bytes', 'read_time', 'write_time']

    def __init__(self, name, init_config, instance, aggregator=None):
        AgentCheck.__init__(self, name, init_config, instance, aggregator)

        self._all_partitions = _is_affirmative(instance.get('all_partitions', False))
        self._file_system_whitelist = instance.get('file_system_whitelist', [])
        self._file_system_blacklist = instance.get('file_system_blacklist', [])
        self._device_whitelist = instance.get('device_whitelist', [])
        self._device_blacklist = instance.get('device_blacklist', [])
        self._mount_point_whitelist = instance.get('mount_point_whitelist', [])
        self._mount_point_blacklist = instance.get('mount_point_blacklist', [])
        self._custom_tags = instance.get('tags', [])

    def check(self, instance):
        partitions = psutil.disk_partitions(all=self._all_partitions)

        for partition in partitions:
            if self._exclude_partition(partition):
                continue

            disk_usage = psutil.disk_usage(partition.mountpoint)
            self._collect_metrics(partition, disk_usage)

        self._collect_io_metrics()

    def _collect_metrics(self, partition, usage):
        metric_tags = [] if self._custom_tags is None else self._custom_tags[:]
        tags = [
            "device:{}".format(partition.device),
            "mount:{}".format(partition.mountpoint),
            "filesystem:{}".format(partition.fstype),
        ]
        metric_tags.extend(tags)

        for name in self.USAGE_ATTRS:
            # For legacy reasons,  the standard unit it kB
            value = getattr(usage, name) / 1024
            value = 0 if value<0 else value
            self.gauge(
                self.METRIC_DISK.format(name),
                value,
                tags=metric_tags
            )

        self.gauge(
            self.METRIC_DISK.format('pct'),
            usage.percent / 100,
            tags=tags
        )

    def _collect_io_metrics(self):
        for disk_name, counters in psutil.disk_io_counters(True).items():
            self.log.debug('IO Counters: {} -> {}'.format(disk_name, counters))

            for counter in self.IO_ATTRS:
                try:
                    name = counter
                    metric_tags = [] if self._custom_tags is None else self._custom_tags[:]
                    metric_tags.append('device:/dev/{}'.format(disk_name))
                    if 'time' in counter:
                        name = "{}_pct".format(counter)
                        # / 1000 as psutil returns the value in ms
                        # x100 to have it as a percentage,
                        # so / 10 in a single op.
                        value = getattr(counters, counter) / 10
                    else:
                        value = getattr(counters, counter)

                    self.rate(self.METRIC_DISK.format(name), value, tags=metric_tags)
                except AttributeError as e:
                    # Some OS don't return read_time/write_time fields
                    # http://psutil.readthedocs.io/en/latest/#psutil.disk_io_counters
                    self.log.debug('IO metrics not collected for {}: {}'.format(disk_name, e))

    def _exclude_partition(self, partition):
        if partition.device in self._device_blacklist:
           return True
        if self._device_whitelist and partition.device not in self._device_whitelist:
            return True
        if partition.mountpoint in self._mount_point_blacklist:
            return True
        if self._mount_point_whitelist and partition.mount not in self._mount_point_whitelist:
            return True
        if partition.fstype in self._file_system_blacklist:
            return True
        if self._file_system_whitelist and partition.fstype not in self._file_system_whitelist:
            return True
