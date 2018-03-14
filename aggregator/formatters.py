# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from .types import MetricTypes


def get_formatter(config):
    formatter = api_formatter

    if config['statsd_metric_namespace']:
        def metric_namespace_formatter_wrapper(metric, value, timestamp, tags,
                                               hostname=None, metric_type=None,
                                               interval=None):

            metric_prefix = config['statsd_metric_namespace']
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
