# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# project
from .types import MetricTypes


def get_formatter(config):
    formatter = api_formatter

    if config['dogstatsd']['metric_namespace']:
        def metric_namespace_formatter_wrapper(metric, value, timestamp, tags,
                                               hostname=None, metric_type=None,
                                               interval=None):

            metric_prefix = config['dogstatsd']['metric_namespace']
            if metric_prefix[-1] != '.':
                metric_prefix += '.'

            return api_formatter(metric_prefix + metric, value, timestamp, tags,
                                 hostname, metric_type, interval)

        formatter = metric_namespace_formatter_wrapper

    return formatter


def api_formatter(metric, value, timestamp, tags, hostname=None,
                  metric_type=None, interval=None):
    return {
        'metric': metric,
        'points': [(timestamp, value)],
        'tags': tags,
        'host': hostname,
        'type': metric_type or MetricTypes.GAUGE,
        'interval': interval,
    }
