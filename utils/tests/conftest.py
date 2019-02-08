# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import signal
import time
import pytest

from aggregator.formatters import api_formatter
from utils.signals import SignalHandler


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
        b'weird.metric.\xe1M1-2-\xe19/16-10K-BB',
        3.14159,
        time.time(),
        [b'key:value', b'env:test']
    )
    payload['series'].append(metric)

    return payload


@pytest.fixture(scope='module')
def signal_handler(request):
    handler = SignalHandler()
    handler.handle(signal.SIGUSR1)

    def cleanup():
        if handler.running():
            handler.stop()
            handler.join()

    request.addfinalizer(cleanup)
    return handler
