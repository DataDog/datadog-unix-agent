# checks/corechecks/net/ntp/tests/test_ntp.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import ntplib
import mock
import pytest

# Updated import path for corecheck
from checks.corechecks.net.ntp.ntp import NTPCheck


@pytest.fixture
def instance():
    return {
        'host': 'foo.com',
        'version': 42,
        'timeout': 13.37,
        'tags': ['mytag'],
    }


@pytest.fixture
def check():
    """
    This check only works in Agent v5 with the old
    AgentCheck api so we mock it.
    (Kept from original test for maximum fidelity)
    """
    c = NTPCheck('ntp', {}, {})
    c.gauge = mock.MagicMock()
    c.service_check = mock.MagicMock()
    return c


@pytest.fixture
def ntp_client():
    request = mock.MagicMock()
    request.return_value = mock.MagicMock(offset=1042, recv_time=4242)
    return mock.MagicMock(request=request)


def test_defaults(check, ntp_client):
    """
    Test what was sent to the NTP client when the config file is empty.
    (Behavior preserved from original bundled tests)
    """
    with mock.patch('checks.corechecks.net.ntp.ntp.ntplib.NTPClient') as c:
        c.return_value = ntp_client
        check.check({})

        args, kwargs = ntp_client.request.call_args

        assert '.datadog.pool.ntp.org' in kwargs.get('host', '')
        assert kwargs.get('port') == 'ntp'
        assert kwargs.get('timeout') == 1.0
        assert kwargs.get('version') == 3

        check.gauge.assert_called_once_with(
            'ntp.offset', 1042, tags=[], timestamp=4242
        )


def test_instance(check, ntp_client, instance):
    """
    Test what was sent to the NTP client when instance config was provided.
    """
    instance['port'] = 'Boo!'
    with mock.patch('checks.corechecks.net.ntp.ntp.ntplib.NTPClient') as c:
        c.return_value = ntp_client
        check.check(instance)

        args, kwargs = ntp_client.request.call_args

        assert kwargs.get('host') == 'foo.com'
        assert kwargs.get('port') == 123                   # fallback behavior
