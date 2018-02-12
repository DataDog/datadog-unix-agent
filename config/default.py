# Defaults
def init(config):
    config_defaults = {
        "dd_url": "https://app.datadoghq.com",
        "app_key": "",
        "hostname": "",
        "tags": [],
        "log_level": "info",
        "forwarder_timeout": 20,
        "forwarder_retry_queue_max_size": 30,
    }

    for k, v in config_defaults.iteritems():
        config.bind_env_and_set_default(k, v)
