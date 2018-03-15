# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# Defaults

DEFAULT_ADDITIONAL_CHECKSD = "/etc/datadog-agent/checks.d"
DEFAULT_DD_URL = "https://app.datadoghq.com"


def init(config):
    config_defaults = {
        "dd_url": DEFAULT_DD_URL,
        "app_key": "",
        "hostname": "",
        "tags": [],
        "log_level": "info",
        "forwarder_timeout": 20,
        "forwarder_retry_queue_max_size": 30,
        "additional_checksd": DEFAULT_ADDITIONAL_CHECKSD,
    }

    for k, v in config_defaults.iteritems():
        config.bind_env_and_set_default(k, v)
