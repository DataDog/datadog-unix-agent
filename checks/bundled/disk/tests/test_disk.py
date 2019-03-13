# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import time
from collections import namedtuple
from pathlib import PurePosixPath

import mock

from aggregator import MetricsAggregator

HOSTNAME = 'foo'
CHECK_NAME = 'disk'

GAUGE = 'gauge'

partition = namedtuple('partition', ['device', 'mountpoint', 'fstype', 'opts'])
usage = namedtuple('usage', ['total', 'used', 'free', 'percent'])
io_counter = namedtuple('io_counter', ['read_count', 'write_count', 'read_bytes',
                                       'write_bytes', 'read_time', 'write_time'])
result = namedtuple('result', ['name', 'value', 'tags'])


MOCK_PARTITIONS = [
    partition(device='/dev/sda1', mountpoint='/', fstype='ext4', opts=''),
    partition(device='/dev/sda2', mountpoint='/var', fstype='ext4', opts=''),
    partition(device='/dev/sda3', mountpoint='/opt', fstype='ext4', opts=''),
    partition(device='/dev/sdb1', mountpoint='/home', fstype='reiserfs', opts=''),
    partition(device='/dev/hda1', mountpoint='/mnt/myhd', fstype='ntfs', opts=''),
]

MOCK_USAGE = {
    '/': usage(total=9876543210, used=1234567890, free=8641975320, percent=12.50),
    '/var': usage(total=9876543210, used=1234567890, free=8641975320, percent=12.50),
    '/opt': usage(total=9876543210, used=1234567890, free=8641975320, percent=12.50),
    '/home': usage(total=9876543210, used=1234567890, free=8641975320, percent=12.50),
    '/mnt/myhd': usage(total=9876543210, used=1234567890, free=8641975320, percent=12.50),
}

MOCK_IO_COUNTERS = {
    'sda1': io_counter(read_count=654321, write_count=123456, read_bytes=65432100,
                       write_bytes=12345600, read_time=300000, write_time=10000),
    'sda2': io_counter(read_count=654321, write_count=123456, read_bytes=65432100,
                       write_bytes=12345600, read_time=300000, write_time=10000),
    'sda3': io_counter(read_count=654321, write_count=123456, read_bytes=65432100,
                       write_bytes=12345600, read_time=300000, write_time=10000),
    'sdb1': io_counter(read_count=654321, write_count=123456, read_bytes=65432100,
                       write_bytes=12345600, read_time=300000, write_time=10000),
    'hdb1': io_counter(read_count=654321, write_count=123456, read_bytes=65432100,
                       write_bytes=12345600, read_time=300000, write_time=10000),
}

def mock_disk_usage(path):
    return MOCK_USAGE.get(path)

def mock_disk_io_counters(perdisk=False, nowrap=True):
    return MOCK_IO_COUNTERS

def generate_expected_gauges():
    total_gauges = 0
    expected_gauges = {}
    for partition in MOCK_PARTITIONS:
        tag_set = ["device:{}".format(PurePosixPath(partition.device).name),
                   "mount:{}".format(partition.mountpoint),
                   "filesystem:{}".format(partition.fstype)]
        usage = MOCK_USAGE[partition.mountpoint]
        for attr in ['total', 'used', 'free', 'percent']:
            value = getattr(usage, attr)
            if 'percent' in attr:
                value /= 100
            else:
                value /= 1024
            metric = attr if attr != 'percent' else 'pct'
            metric_name = "system.disk.{}".format(metric)
            if metric_name in expected_gauges:
                expected_gauges[metric_name].append(
                    result(name=metric_name, value=value, tags=tag_set))
            else:
                expected_gauges[metric_name] = [result(name=metric_name, value=value, tags=tag_set)]

            total_gauges += 1

    return total_gauges, expected_gauges

def generate_expected_rates():
    total_rates = 0
    expected_rates = {}
    for device, counter in MOCK_IO_COUNTERS.items():
        tag_set = ["device:{}".format(device)]
        for attr in ['read_count', 'write_count', 'read_bytes', 'write_bytes', 'read_time', 'write_time']:
            metric = "system.disk.{}".format(attr)
            if 'time' in attr:
                metric = "{}_pct".format(metric)
            # NOTE: all rates have a value of zero (ie. the delta = 0)
            if metric in expected_rates:
                expected_rates[metric].append(result(name=metric, value=0, tags=tag_set))
            else:
                expected_rates[metric] = [result(name=metric, value=0, tags=tag_set)]

            total_rates += 1

    return total_rates, expected_rates

def is_metric_expected(expectations, metric):
    name = metric['metric']
    tags = list(metric['tags'])

    if name not in expectations:
        return False

    metric_list = expectations[name]
    for m in metric_list:
        if sorted(tags) == sorted(m.tags) or \
                sorted(tags) == sorted([tag.encode('utf-8') for tag in m.tags]):
            if metric['points'][0][1] == m.value:
                return True

    return False

@mock.patch('psutil.disk_partitions')
@mock.patch('psutil.disk_usage', side_effect=mock_disk_usage)
@mock.patch('psutil.disk_io_counters', side_effect=mock_disk_io_counters)
def test_disk_basic(disk_io_counters, disk_usage, disk_partitions):
    from datadog_checks.disk import Disk  # delayed import for good patching

    disk_partitions.return_value = MOCK_PARTITIONS

    aggregator = MetricsAggregator(
        HOSTNAME,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    total_gauges, expected_gauges = generate_expected_gauges()
    total_rates, expected_rates = generate_expected_rates()

    c = Disk("disk", {}, {}, aggregator)
    c.check({})

    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric
    assert len(metrics) == total_gauges

    time.sleep(1)

    c.check({})
    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    assert len(metrics) == (total_gauges + total_rates)
    for metric in metrics:
        assert metric['metric'] in expected_gauges or metric['metric'] in expected_rates
        assert len(metric['points']) == 1
        assert metric['host'] == HOSTNAME
        assert metric['type'] == GAUGE
        assert is_metric_expected(expected_gauges, metric) or is_metric_expected(expected_rates, metric)
