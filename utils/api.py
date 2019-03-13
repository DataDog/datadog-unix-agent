# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging

import requests

from utils.network import get_proxy


log = logging.getLogger(__name__)


def validate_api_key(config):
    try:
        proxy = get_proxy()

        r = requests.get("%s/api/v1/validate" % config.get('dd_url').rstrip('/'),
            params={'api_key': config.get('api_key')}, proxies=proxy,
            timeout=3, verify=(not config.get('skip_ssl_validation', False)))

        if r.status_code == 403:
            return "[ERROR] API Key is invalid"

        r.raise_for_status()

    except requests.RequestException:
        return "[ERROR] Unable to validate API Key. Please try again later"
    except Exception:
        log.exception("Unable to validate API Key")
        return "[ERROR] Unable to validate API Key (unexpected error). Please try again later"

    return "API Key is valid"
