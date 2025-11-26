# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock
import sys
import platform
import psutil
import socket
import time

from config.config import AGENT_VERSION
from metadata import metadata

@mock.patch('platform.node', return_value='test-hostname')
@mock.patch('uuid.getnode', return_value=11111111111)
@mock.patch('time.time', return_value=1234567890.12)
@mock.patch(
    'config.config.get',
    side_effect=lambda key, default=None: (
        # tags
        ['tag1', 'tag2'] if key == 'tags'
        # api_key (raw, masking done in metadata.get_common)
        else 'my_api_key' if key == 'api_key'
        # disable gohai for this test so payload matches legacy expectation
        else False if key == 'enable_gohai'
        # everything else -> default
        else default
    )
)
@mock.patch('utils.platform.Platform.is_linux', return_value=False)
@mock.patch('utils.platform.Platform.is_freebsd', return_value=False)
@mock.patch('metadata.metadata.get_os', return_value='test_os')
def test_get_metadata(get_os, is_freebsd, is_linux, config_get, time_time, uuid_getnode, platform_node):
    # api_key masking logic for 'my_api_key':
    # masked_api_key = '*' * 27 + last 5 chars
    masked_api_key = '***************************i_key'
    res = {
        'agentVersion': AGENT_VERSION,
        'apiKey': masked_api_key,
        'uuid': '9ef19c3f1a4c5493825695cd864dc2c3',
        'internalHostname': 'test',
        'os': 'test_os',
        'python': sys.version,
        'systemStats': {
            'machine': platform.machine(),
            'platform': sys.platform,
            'processor': platform.processor(),
            'pythonV': platform.python_version(),
            'cpuCores': psutil.cpu_count(),
        },
        'meta': {
            'socket-hostname': socket.gethostname(),
            'timezones': time.tzname,
            'host_aliases': [],
            'socket-fqdn': socket.getfqdn(),
            'hostname': 'test',
        },
        'host-tags': {'system': ['tag1', 'tag2']},
        'resources': {
            'meta': {'host': 'test'},
            'processes': {'snaps': []},
        },
        'events': {},
    }
    assert res == metadata.get_metadata('test', AGENT_VERSION)

    res['events'].update({
        'System': [
            {
                'event_type': 'Agent Startup',
                'host': 'test',
                'msg_text': f'Version {AGENT_VERSION}',
                'timestamp': 1234567890.12
            }
        ]
    })
    assert res == metadata.get_metadata('test', AGENT_VERSION, start_event=True)
