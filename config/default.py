# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# Defaults

DEFAULT_ADDITIONAL_CHECKSD = "/etc/datadog-agent/checks.d"
DEFAULT_DD_URL = "https://app.datadoghq.com"
DEFAULT_FORWARDER_TO = 20
DEFAULT_FORWARDER_RETRY_Q_MAX_SIZE = 30
DEFAULT_HOST_METADATA_INTERVAL = 4 * 60 * 60
DEFAULT_EXT_HOST_TAGS_INTERVAL = 5 * 60
DEFAULT_LOG_LEVEL = 'info'


def init(config):
    config_defaults = {
        "dd_url": DEFAULT_DD_URL,
        "app_key": "",
        "hostname": "",
        "tags": [],
        "log_level": DEFAULT_LOG_LEVEL,
        "forwarder_timeout": DEFAULT_FORWARDER_TO,
        "forwarder_retry_queue_max_size": DEFAULT_FORWARDER_RETRY_Q_MAX_SIZE,
        "additional_checksd": DEFAULT_ADDITIONAL_CHECKSD,
        "host_metadata": DEFAULT_HOST_METADATA_INTERVAL,
        "external_host_tags": DEFAULT_EXT_HOST_TAGS_INTERVAL,
    }

    for k, v in config_defaults.iteritems():
        config.bind_env_and_set_default(k, v)
