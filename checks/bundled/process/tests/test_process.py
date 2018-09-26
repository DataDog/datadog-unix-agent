# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
from mock import patch
import psutil

from datadog_checks.process import Process
from aggregator import MetricsAggregator

import pytest

# cross-platform switches
_PSUTIL_IO_COUNTERS = True
try:
    p = psutil.Process(os.getpid())
    p.io_counters()
except Exception:
    _PSUTIL_IO_COUNTERS = False

_PSUTIL_MEM_SHARED = True
try:
    p = psutil.Process(os.getpid())
    p.memory_info_ex().shared
except Exception:
    _PSUTIL_MEM_SHARED = False

HOSTNAME = 'foo'
CHECK_NAME = 'process'

PROCESS_METRICS = [
    'system.processes.ctx_swt.involuntary',
    'system.processes.io.r_bytes',
    'system.processes.io.r_count',
    'system.processes.io.w_bytes',
    'system.processes.io.w_count',
    'system.processes.mem.pct',
    'system.processes.mem.real',
    'system.processes.mem.rss',
    'system.processes.mem.vms',
    'system.processes.number',
    'system.processes.open_file_descriptors',
    'system.processes.threads',
    'system.processes.ctx_swt.voluntary',
    'system.processes.run_time.avg',
    'system.processes.run_time.max',
    'system.processes.run_time.min',
]

GAUGE = 'gauge'

def get_config_stubs():
    return [
        {
            'instance': {
                'name': 'test_0',
                # index in the array for our find_pids mock
                'search_string': ['test_0'],
                'thresholds': {
                    'critical': [2, 4],
                    'warning': [1, 5]
                }
            },
            'mocked_processes': set()
        },
        {
            'instance': {
                'name': 'test_1',
                # index in the array for our find_pids mock
                'search_string': ['test_1'],
                'thresholds': {
                    'critical': [1, 5],
                    'warning': [2, 4]
                }
            },
            'mocked_processes': set([1])
        },
        {
            'instance': {
                'name': 'test_2',
                # index in the array for our find_pids mock
                'search_string': ['test_2'],
                'thresholds': {
                    'critical': [2, 5],
                    'warning': [1, 4]
                }
            },
            'mocked_processes': set([22, 35])
        },
        {
            'instance': {
                'name': 'test_3',
                # index in the array for our find_pids mock
                'search_string': ['test_3'],
                'thresholds': {
                    'critical': [1, 4],
                    'warning': [2, 5]
                }
            },
            'mocked_processes': set([1, 5, 44, 901, 34])
        },
        {
            'instance': {
                'name': 'test_4',
                # index in the array for our find_pids mock
                'search_string': ['test_4'],
                'thresholds': {
                    'critical': [1, 4],
                    'warning': [2, 5]
                }
            },
            'mocked_processes': set([3, 7, 2, 9, 34, 72])
        },
        {
            'instance': {
                'name': 'test_tags',
                # index in the array for our find_pids mock
                'search_string': ['test_5'],
                'tags': ['onetag', 'env:prod']
            },
            'mocked_processes': set([2])
        },
        {
            'instance': {
                'name': 'test_badthresholds',
                # index in the array for our find_pids mock
                'search_string': ['test_6'],
                'thresholds': {
                    'test': 'test'
                }
            },
            'mocked_processes': set([89])
        },
        {
            'instance': {
                'name': 'test_7',
                # index in the array for our find_pids mock
                'search_string': ['test_7'],
                'thresholds': {
                    'critical': [2, 4],
                    'warning': [1, 5]
                }
            },
            'mocked_processes': set([1])
        },
        {
            'instance': {
                'name': 'test_8',
                'pid': 1,
            },
            'mocked_processes': set([1])
        },
        {
            'instance': {
                'name': 'test_9',
                'pid_file': 'process/test/ci/fixtures/test_pid_file',
            },
            'mocked_processes': set([1])
        }
    ]

class MockProcess(object):
    def __init__(self):
        self.pid = None

    def is_running(self):
        return True

    def children(self, recursive=False):
        return []


def get_psutil_proc():
    return psutil.Process(os.getpid())


@pytest.fixture
def aggregator():
    aggregator = MetricsAggregator(
        HOSTNAME,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    return aggregator


def test_psutil_wrapper_simple(aggregator):
    # Load check with empty config
    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    name = myprocess.psutil_wrapper(
        get_psutil_proc(),
        'name',
        None,
    )
    assert name is not None


def test_psutil_wrapper_simple_fail(aggregator):
    # Load check with empty config
    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    name = myprocess.psutil_wrapper(
        get_psutil_proc(),
        'blah',
        None,
        False
    )
    assert name is None


def test_psutil_wrapper_accessors(aggregator):
    # Load check with empty config
    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    meminfo = myprocess.psutil_wrapper(
        get_psutil_proc(),
        'memory_info',
        ['rss', 'vms', 'foo'],
    )
    assert 'rss' in meminfo
    assert 'vms' in meminfo
    assert 'foo' not in meminfo


def test_psutil_wrapper_accessors_fail(aggregator):
    # Load check with empty config
    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    meminfo = myprocess.psutil_wrapper(
        get_psutil_proc(),
        'memory_infoo',
        ['rss', 'vms'],
        False
    )
    assert 'rss' not in meminfo
    assert 'vms' not in meminfo


def test_ad_cache(aggregator):
    config = {
        'instance': {
            'name': 'python',
            'search_string': ['python'],
            'ignore_denied_access': False,
        }
    }
    myprocess = Process(CHECK_NAME, {}, config['instance'], aggregator)

    def deny_name(obj):
        raise psutil.AccessDenied()

    with patch.object(psutil.Process, 'name', deny_name):
        with pytest.raises(psutil.AccessDenied):
            myprocess.check(config['instance'])

    assert len(myprocess.ad_cache) > 0

    # The next run shouldn't throw an exception
    myprocess.check(config['instance'])
    # The ad cache should still be valid
    assert myprocess.should_refresh_ad_cache('python') is False

    # Reset caches
    myprocess.last_ad_cache_ts = {}
    myprocess.last_pid_cache_ts = {}

    # Shouldn't throw an exception
    myprocess.check(config['instance'])


def mock_find_pid(name, search_string, exact_match=True, ignore_ad=True,
                  refresh_ad_cache=True):
    if search_string is not None:
        idx = search_string[0].split('_')[1]

    config_stubs = get_config_stubs()
    return config_stubs[int(idx)]['mocked_processes']


def mock_psutil_wrapper(process, method, accessors, try_sudo, *args, **kwargs):
    if method == 'num_handles':  # win32 only
        return None
    if accessors is None:
        result = 0
    else:
        result = dict([(accessor, 0) for accessor in accessors])
    return result


def generate_expected_tags(instance, service_check=False):
    proc_name = instance['name']
    expected_tags = [proc_name, "process_name:{0}".format(proc_name)]
    if 'tags' in instance:
        expected_tags += instance['tags']
    if service_check:
        expected_tags += ["process:{}".format(proc_name)]

    return sorted(expected_tags)


@patch('psutil.Process', return_value=MockProcess())
def test_check(mock_process, aggregator):

    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    config = get_config_stubs()
    for idx in range(len(config)):
        instance = config[idx]['instance']
        if 'search_string' not in instance.keys():
            myprocess.check(instance)
        else:
            with patch('datadog_checks.process.Process.find_pids',
                       return_value=mock_find_pid(instance['name'], instance['search_string'])):
                myprocess.check(instance)
                # test for something


@patch('psutil.Process', return_value=MockProcess())
def test_check_collect_children(mock_process, aggregator):
    instance = {
        'name': 'foo',
        'pid': 1,
        'collect_children': True
    }
    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    myprocess.check(instance)

    expected_metrics = {
        'system.processes.number': (GAUGE, 1, generate_expected_tags(instance))
    }
    metrics = myprocess.aggregator.flush()
    for metric in metrics[:-1]:
        assert metric['metric'] in expected_metrics
        mtype, mval, mtags = expected_metrics[metric['metric']]
        assert len(metric['points']) == 1
        assert metric['points'][0][1] == mval
        assert metric['host'] == HOSTNAME
        assert metric['type'] == mtype
        assert list(metric['tags']) == mtags


@patch('psutil.Process', return_value=MockProcess())
def test_check_filter_user(mock_process, aggregator):
    instance = {
        'name': 'foo',
        'pid': 1,
        'user': 'Bob'
    }

    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    with patch('datadog_checks.process.Process._filter_by_user', return_value={1, 2}):
        myprocess.check(instance)

    expected_metrics = {
        'system.processes.number': (GAUGE, 2, generate_expected_tags(instance))
    }
    metrics = myprocess.aggregator.flush()
    for metric in metrics[:-1]:
        assert metric['metric'] in expected_metrics
        mtype, mval, mtags = expected_metrics[metric['metric']]
        assert len(metric['points']) == 1
        assert metric['points'][0][1] == mval
        assert metric['host'] == HOSTNAME
        assert metric['type'] == mtype
        assert list(metric['tags']) == mtags


def test_check_missing_pid(aggregator):
    instance = {
        'name': 'foo',
        'pid_file': '/foo/bar/baz'
    }
    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    myprocess.check(instance)

    expected_service_checks = {
        'process.up': (Process.CRITICAL, generate_expected_tags(instance, True))
    }
    service_checks = myprocess.aggregator.flush_service_checks()

    assert len(service_checks) == 1
    for sc in service_checks:
        assert sc['check'] in expected_service_checks
        mstatus, mtags = expected_service_checks[sc['check']]
        assert sc['host_name'] == HOSTNAME
        assert sc['status'] == mstatus
        assert sorted(list(sc['tags'])) == mtags


def test_check_real_process(aggregator):
    "Check that we detect python running (at least this process)"

    instance = {
        'name': 'py',
        'search_string': ['python'],
        'exact_match': False,
        'ignored_denied_access': True,
        'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
    }
    myprocess = Process(CHECK_NAME, {}, {}, aggregator)
    expected_tags = generate_expected_tags(instance)
    myprocess.check(instance)

    metrics = myprocess.aggregator.flush()
    for metric in metrics[:-1]:
        assert metric['metric'] in PROCESS_METRICS
        assert sorted(list(metric['tags'])) == expected_tags

    expected_service_checks = {
        'process.up': (Process.OK, generate_expected_tags(instance, True))
    }
    service_checks = myprocess.aggregator.flush_service_checks()

    assert len(service_checks) == 1
    for sc in service_checks:
        assert sc['check'] in expected_service_checks
        mstatus, mtags = expected_service_checks[sc['check']]
        assert sc['host_name'] == HOSTNAME
        assert sc['status'] == mstatus
        assert sorted(list(sc['tags'])) == mtags

    # this requires another run
    expected_metrics = {
        'system.processes.cpu.pct': (GAUGE, generate_expected_tags(instance)),
        'system.processes.cpu.normalized_pct': (GAUGE, generate_expected_tags(instance)),
    }

    myprocess.check(instance)
    metrics = myprocess.aggregator.flush()
    asserted = set()
    for metric in metrics[:-1]:
        if metric['metric'] not in expected_metrics:
            continue

        asserted.add(metric['metric'])
        mtype, mtags = expected_metrics[metric['metric']]
        assert len(metric['points']) == 1
        assert metric['host'] == HOSTNAME
        assert metric['type'] == mtype
        assert list(metric['tags']) == mtags

    assert len(asserted) == len(expected_metrics)
