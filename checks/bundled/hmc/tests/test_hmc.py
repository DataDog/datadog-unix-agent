# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from datadog_checks.hmc import HMC
from aggregator import MetricsAggregator

import os
import pytest
from mock import patch

import paramiko


HOSTNAME = 'foo'
CHECK_NAME = 'hmc'

__here__ = os.path.dirname(__file__)

def get_config_stubs():
    return [{
        'instance': {
            'name': 'test_0',
            'host': 'foo',
            'port': 22,
            'username': 'bruce_banner',
            'password': None,
            'private_key_file': 'id_rsa',
            'private_key_type': 'rsa',
            'add_missing_keys': [],
        }
    }]

class FakeSSHClient(object):
    CMD_FIXTURE_MAP = {
        HMC.HMC_GET_VERSION: os.path.join(__here__, 'fixtures','lshmc.txt'),
        HMC.HMC_MEMINFO_CMD: os.path.join(__here__, 'fixtures', 'hmc_meminfo.txt'),
        HMC.HMC_MON_CMD: os.path.join(__here__, 'fixtures', 'hmc_monhmc.txt'),
        'lssyscfg -r sys': os.path.join(__here__, 'fixtures','lssyscfg.sys.txt'),
        'lssyscfg -r lpar': {
            '-m DD00': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD00.txt'),
            '-m DD01': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD01.txt'),
            '-m DD02': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD02.txt'),
            '-m DD03': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD03.txt'),
            '-m DD04': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD04.txt'),
            '-m DD05': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD05.txt'),
            '-m DD06': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD06.txt'),
            '-m DD07': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD07.txt'),
            '-m DD08': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD08.txt'),
            '-m DD09': os.path.join(__here__, 'fixtures','lssyscfg.lpar.DD09.txt'),
        },
        'lslparutil -r config': {
            '-m DD00': os.path.join(__here__, 'fixtures','lslparutil.config.DD00.txt'),
            '-m DD01': os.path.join(__here__, 'fixtures','lslparutil.config.DD01.txt'),
            '-m DD02': os.path.join(__here__, 'fixtures','lslparutil.config.DD02.txt'),
            '-m DD03': os.path.join(__here__, 'fixtures','lslparutil.config.DD03.txt'),
            '-m DD04': os.path.join(__here__, 'fixtures','lslparutil.config.DD04.txt'),
            '-m DD05': os.path.join(__here__, 'fixtures','lslparutil.config.DD05.txt'),
            '-m DD06': os.path.join(__here__, 'fixtures','lslparutil.config.DD06.txt'),
            '-m DD07': os.path.join(__here__, 'fixtures','lslparutil.config.DD07.txt'),
            '-m DD08': os.path.join(__here__, 'fixtures','lslparutil.config.DD08.txt'),
            '-m DD09': os.path.join(__here__, 'fixtures','lslparutil.config.DD09.txt'),
        },
        'lslparutil -r hmc': os.path.join(__here__, 'fixtures','lslparutil.hmc.txt'),
        'lslparutil -r lpar': os.path.join(__here__, 'fixtures','lslparutil.lpar.txt'),
        'lslparutil -r pool': os.path.join(__here__, 'fixtures','lslparutil.pool.txt'),
        'lslparutil -r procpool': os.path.join(__here__, 'fixtures','lslparutil.procpool.txt'),
        'lslparutil -r mempool': os.path.join(__here__, 'fixtures','lslparutil.mempool.txt'),
        'lslparutil -r sys': os.path.join(__here__, 'fixtures','lslparutil.sys.txt'),
    }

    def connect(self, ip, port=22, username=None, password=None,
                pkey=None, key_filename=None, look_for_keys=None, timeout=10):
        pass

    def close(self):
        pass

    def set_missing_host_key_policy(self, policy):
        pass

    def load_system_host_keys(self):
        pass

    def exec_command(self, cmd, environment={}):
        # direct match
        if cmd in self.CMD_FIXTURE_MAP:
            fixture = self.CMD_FIXTURE_MAP[cmd]
            return None, open(fixture), None

        cmd_split = cmd.split()
        fixture = self.CMD_FIXTURE_MAP.get(' '.join(cmd_split[0:3]))
        if isinstance(fixture, dict):
            try:
                fixture = fixture.get(' '.join(cmd_split[3:5]))
            except IndexError:
                fixture = fixture.get(cmd_split[3:])

        if not fixture:
            return None, None, None

        return None, open(fixture), None


@pytest.fixture
def aggregator():
    aggregator = MetricsAggregator(
        HOSTNAME,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    return aggregator


def test_simple_hmc(aggregator):
    with patch.object(paramiko, 'SSHClient', return_value=FakeSSHClient()):
        # Load check with basic config
        instance = {
            'host': 'localhost',
            'username': 'foo',
            'password': 'bar',
            'port': 22,
        }
        myhmc = HMC(CHECK_NAME, {}, {}, aggregator)
        myhmc.check(instance)

