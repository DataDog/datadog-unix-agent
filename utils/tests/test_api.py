# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import requests  # noqa: F401

from utils.api import (
    validate_api_key,
    VALID_API_KEY_MSG,
    INVALID_API_KEY_MSG,
    REQUEST_ERROR_MSG,
    OTHER_ERROR_MSG,
)
from config import config


def test_validate_api_key(requests_mock):
    url = "{}/api/v1/validate".format(config.get('dd_url').rstrip('/'))
    config.set('api_key', 'somerandomkey')

    requests_mock.register_uri('GET', url, status_code=200)

    validation = validate_api_key(config)
    assert validation == VALID_API_KEY_MSG

    requests_mock.register_uri('GET', url, status_code=403)
    validation = validate_api_key(config)
    assert validation == INVALID_API_KEY_MSG

    requests_mock.register_uri('GET', url, exc=requests.exceptions.ConnectTimeout)
    validation = validate_api_key(config)
    assert validation == REQUEST_ERROR_MSG

    requests_mock.register_uri('GET', url, exc=Exception)
    validation = validate_api_key(config)
    assert validation == OTHER_ERROR_MSG
