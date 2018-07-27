# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from checks.corechecks.system import iostat
from aggregator import MetricsAggregator


GAUGE = 'gauge'
AIX_MOCK_IOSTAT = '''
System configuration: lcpu=4 drives=2 paths=2 vdisks=1 tapes=0

System: sovma448
                           Kbps      tps    Kb_read   Kb_wrtn
      Physical             0.0       0.0          0         0

Vadapter:                        xfers                                 read                        write                              queue
-------------------- --------------------------------------- -------------------------- -------------------------- --------------------------------------
                       Kbps   tps bkread bkwrtn partition-id   rps    avg    min    max   wps    avg    min    max    avg    min    max   avg   avg  serv
                                                                     serv   serv   serv         serv   serv   serv   time   time   time  wqsz  sqsz qfull
vscsi0                  0.0   0.0    0.0    0.0            1   0.0   0.0    0.0    0.0    0.0   0.0    0.0    0.0    0.0    0.0    0.0    0.0   0.0   0.0


Disks:                           xfers                                read                                write                                  queue
-------------------- -------------------------------- ------------------------------------ ------------------------------------ --------------------------------------
                       %tm    bps   tps  bread  bwrtn   rps    avg    min    max time fail   wps    avg    min    max time fail    avg    min    max   avg   avg  serv
                       act                                    serv   serv   serv outs              serv   serv   serv outs        time   time   time  wqsz  sqsz qfull
hdisk1                 0.0   0.0    0.0   0.0    0.0    0.0   0.0    0.0    0.0     0    0   0.0   0.0    0.0    0.0     0    0   0.0    0.0    0.0    0.0   0.0   0.0
hdisk0                 0.0   0.0    0.0   0.0    0.0    0.0   0.0    0.0    0.0     0    0   0.0   0.0    0.0    0.0     0    0   0.0    0.0    0.0    0.0   0.0   0.0
'''

@mock.patch("checks.corechecks.system.iostat.get_subprocess_output", return_value=(AIX_MOCK_IOSTAT, None, None))
def test_iostat_aix(get_subprocess_output):
    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )


    import pdb ; pdb.set_trace()
    c = iostat.IOStat("iostat", {}, {}, aggregator)
    c.check({})
    metrics = c.aggregator.flush()

    expected_metrics = {
        'system.iostat.vadapter.xfers.kbps': GAUGE,
        'system.iostat.vadapter.xfers.tps': GAUGE,
        'system.iostat.vadapter.xfers.blks.read': GAUGE,
        'system.iostat.vadapter.xfers.blks.write': GAUGE,
        'system.iostat.vadapter.read.rps': GAUGE,
        'system.iostat.vadapter.read.serv.avg': GAUGE,
        'system.iostat.vadapter.read.serv.min': GAUGE,
        'system.iostat.vadapter.read.serv.max': GAUGE,
        'system.iostat.vadapter.write.wps': GAUGE,
        'system.iostat.vadapter.write.serv.avg': GAUGE,
        'system.iostat.vadapter.write.serv.min': GAUGE,
        'system.iostat.vadapter.write.serv.max': GAUGE,
        'system.iostat.vadapter.queue.time.avg': GAUGE,
        'system.iostat.vadapter.queue.time.min': GAUGE,
        'system.iostat.vadapter.queue.time.max': GAUGE,
        'system.iostat.vadapter.queue.wqsz.avg': GAUGE,
        'system.iostat.vadapter.queue.sqsz.avg': GAUGE,
        'system.iostat.vadapter.queue.serv.qfull': GAUGE,
        'system.iostat.disks.xfers.tm.act.pct': GAUGE,
        'system.iostat.disks.xfers.bps': GAUGE,
        'system.iostat.disks.xfers.tps': GAUGE,
        'system.iostat.disks.xfers.blks.read': GAUGE,
        'system.iostat.disks.xfers.blks.write': GAUGE,
        'system.iostat.disks.read.rps': GAUGE,
        'system.iostat.disks.read.serv.avg': GAUGE,
        'system.iostat.disks.read.serv.min': GAUGE,
        'system.iostat.disks.read.serv.max': GAUGE,
        'system.iostat.disks.read.timeouts': GAUGE,
        'system.iostat.disks.read.fail': GAUGE,
        'system.iostat.disks.write.wps': GAUGE,
        'system.iostat.disks.write.serv.avg': GAUGE,
        'system.iostat.disks.write.serv.min': GAUGE,
        'system.iostat.disks.write.serv.max': GAUGE,
        'system.iostat.disks.write.timeouts': GAUGE,
        'system.iostat.disks.write.fail': GAUGE,
        'system.iostat.disks.queue.time.avg': GAUGE,
        'system.iostat.disks.queue.time.min': GAUGE,
        'system.iostat.disks.queue.time.max': GAUGE,
        'system.iostat.disks.queue.wqsz.avg': GAUGE,
        'system.iostat.disks.queue.sqsz.avg': GAUGE,
        'system.iostat.disks.queue.serv.qfull': GAUGE,
    }

    # we subtract two - one for /proc, and one for the heading
    # assert len(metrics) == len(expected_metrics) * (len(filter(None, AIX_MOCK_IOSTAT.splitlines())) - 2)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
        assert len(metric['points']) == 1
        assert metric['host'] == hostname
        assert metric['type'] == expected_metrics[metric['metric']]
