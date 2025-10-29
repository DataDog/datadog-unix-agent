# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging

import requests

from utils.network import get_site_url
from utils.http import get_shared_requests

log = logging.getLogger(__name__)

VALID_API_KEY_MSG = "API Key is valid"
INVALID_API_KEY_MSG = "[ERROR] API Key is invalid"
REQUEST_ERROR_MSG = "[ERROR] Unable to validate API Key. Please try again later"
OTHER_ERROR_MSG = "[ERROR] Unable to validate API Key (unexpected error). Please try again later"


def validate_api_key(config):
    shared_requests = get_shared_requests()
    try:
        base_uri = get_site_url(config.get('dd_url'), site=config.get('site'))
        r = shared_requests.get("{}/api/v1/validate".format(base_uri.rstrip('/')),
                                timeout=3, headers={'DD-API-KEY': config.get('api_key')})

        if r.status_code == 403:
            return INVALID_API_KEY_MSG

        r.raise_for_status()

    except requests.RequestException:
        return REQUEST_ERROR_MSG
    except Exception:
        log.exception("Unable to validate API Key")
        return OTHER_ERROR_MSG

    return VALID_API_KEY_MSG
