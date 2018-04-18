# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# Defaults

DEFAULT_ADDITIONAL_CHECKSD = '/etc/datadog-agent/checks.d'
DEFAULT_DD_URL = 'https://app.datadoghq.com'
DEFAULT_MIN_COLLECTION_INTERVAL = 15
DEFAULT_AGGREGATOR_INTERVAL = 1.0
DEFAULT_AGGREGATOR_EXPIRY_SECS = 300
DEFAULT_FORWARDER_TO = 20
DEFAULT_FORWARDER_RETRY_Q_MAX_SIZE = 30
DEFAULT_HOST_METADATA_INTERVAL = 4 * 60 * 60
DEFAULT_EXT_HOST_TAGS_INTERVAL = 5 * 60
DEFAULT_LOG_LEVEL = 'info'
DEFAULT_DOGSTATSD_PORT = 8125
DEFAULT_BIND_HOST = 'localhost'

# This is used to ensure that metrics with a timestamp older than
# RECENT_POINT_THRESHOLD_DEFAULT seconds (or the value passed in to
# the MetricsAggregator constructor) get discarded rather than being
# input into the incorrect bucket. Currently, the MetricsAggregator
# does not support submitting values for the past, and all values get
# submitted for the timestamp passed into the flush() function.
# The MetricsBucketAggregator uses times that are aligned to "buckets"
# that are the length of the interval that is passed into the
# MetricsBucketAggregator constructor.
DEFAULT_RECENT_POINT_THRESHOLD = 3600


def init(config):
    config_defaults = {
        'dd_url': DEFAULT_DD_URL,
        'api_key': '',
        'hostname': '',
        'tags': [],
        'log_level': DEFAULT_LOG_LEVEL,
        'forwarder_timeout': DEFAULT_FORWARDER_TO,
        'forwarder_retry_queue_max_size': DEFAULT_FORWARDER_RETRY_Q_MAX_SIZE,
        'additional_checksd': DEFAULT_ADDITIONAL_CHECKSD,
        'host_metadata_interval': DEFAULT_HOST_METADATA_INTERVAL,
        'external_host_tags_interval': DEFAULT_EXT_HOST_TAGS_INTERVAL,
        'min_collection_interval': DEFAULT_MIN_COLLECTION_INTERVAL,
        'aggregator_interval': DEFAULT_AGGREGATOR_INTERVAL,
        'aggregator_expiry_seconds': DEFAULT_AGGREGATOR_EXPIRY_SECS,
        'recent_point_threshold': DEFAULT_RECENT_POINT_THRESHOLD,
        'bind_host': DEFAULT_BIND_HOST,
        'dogstatsd': {
            'port': DEFAULT_DOGSTATSD_PORT,
            'non_local_traffic': False,
            'forward_host': None,
            'forward_port': None,
            'so_rcvbuf': None,
            'metric_namespace': None,
            'utf8_decoding': False,
        },
    }

    for k, v in config_defaults.iteritems():
        config.bind_env_and_set_default(k, v)
