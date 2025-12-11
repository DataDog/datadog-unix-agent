# checks/corechecks/system/filesystem/tests/test_filesystem.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from aggregator import MetricsAggregator
from checks.corechecks.system.filesystem.filesystem import FilesystemCheck

GAUGE = 'gauge'

AIX_MOCK_FS = '''
Filesystem    MB blocks      Used Available Capacity Mounted on
/dev/hd4         768.00    304.87    463.13      40% /
/dev/hd2        8448.00   2583.39   5864.61      31% /usr
/dev/hd9var      768.00    657.10    110.90      86% /var
/dev/hd3         256.00    160.73     95.27      63% /tmp
/dev/hd1         256.00    220.36     35.64      87% /home
/dev/hd11admin    256.00      0.38    255.62       1% /admin
/proc                 -         -         -       -  /proc
/dev/hd10opt    3072.00   1209.05   1862.95      40% /opt
/dev/livedump    256.00      0.36    255.64       1% /var/adm/ras/livedump
/dev/resgrp448lv  81920.00     12.83  81907.17       1% /resgrp448
192.168.253.80:/usr/sys/inst.images/toolbox_20110809  15360.00  13208.85   2151.15      86% /toolbox_20110809
192.168.253.80:/usr/sys/inst.images/toolbox_20131113  15360.00  13208.85   2151.15      86% /toolbox_20131113
192.168.253.80:/usr/sys/inst.images/toolbox_20151220  15360.00  13208.85   2151.15      86% /toolbox_20151220
192.168.253.80:/usr/sys/inst.images/mozilla_3513  15360.00  13208.85   2151.15      86% /mozilla
192.168.253.80:/export/lpp_source/aix/aix_6100-09-06 152640.00 138583.53  14056.47      91% /mnt
'''


@mock.patch(
    "checks.corechecks.system.filesystem.filesystem.get_subprocess_output",
    return_value=(AIX_MOCK_FS, None, None)
)
def test_load_aix(mock_subproc):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = FilesystemCheck("fs", {}, {}, aggregator)
    c.check({})

    metrics = c.aggregator.flush()[:-1]  # we remove the datadog.agent.running metric

    expected_metrics = {
        'system.fs.total': GAUGE,
        'system.fs.used': GAUGE,
        'system.fs.available': GAUGE,
        'system.fs.available.pct': GAUGE,
    }

    # we subtract two - one for /proc, and one for the heading
    assert len(metrics) == len(expected_metrics) * (len([_f for _f in AIX_MOCK_FS.splitlines() if _f]) - 2)

    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert metric['type'] == expected_metrics[metric['metric']]
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
