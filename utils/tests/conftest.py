# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import pytest
import time

from aggregator.formatters import api_formatter


@pytest.fixture(scope='session')
def unicode_payload():
    payload = {
        'series': []
    }
    metric = api_formatter(
        'foo.bar',
        1.0,
        time.time(),
        ['key:value', 'env:test']
    )
    payload['series'].append(metric)
    metric = api_formatter(
        'weird.metric.\xe1M1-2-\xe19/16-10K-BB',
        3.14159,
        time.time(),
        ['key:value', 'env:test']
    )
    payload['series'].append(metric)

    return payload
