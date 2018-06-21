# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from checks.corechecks.system import lparstats
from aggregator import MetricsAggregator

GAUGE = 'gauge'

AIX_LPARSTATS_MEMORY = '''

        System configuration: lcpu=4 mem=7936MB mpsz=0.00GB iome=7936.00MB iomp=16 ent=0.20

        physb   hpi  hpit  pmem  iomin   iomu   iomf  iohwm iomaf %entc  vcsw
        ----- ----- ----- ----- ------ ------ ------ ------ ----- ----- -----
         0.63     0     0  7.75   46.8   -     -     -       0   4.1 1249045057
'''
AIX_LPARSTATS_MEMORY_PAGE = '''

        System configuration: lcpu=4 mem=7936MB mpsz=0.00GB iome=7936.00MB iomp=16 ent=0.20

        physb   hpi  hpit  pmem  iomin   iomu   iomf  iohwm iomaf  pgcol mpgcol ccol %entc  vcsw
        ----- ----- ----- ----- ------ ------ ------ ------ ----- ------ ------ ---- ----- -----
        0.63     0     0  7.75   46.8   23.8   -     23.9     0    0.0   0.0   0.0   4.1 1249055296
'''
AIX_LPARSTATS_MEMORY_ENTITLEMENTS = '''

System configuration: lcpu=4 mem=7936MB mpsz=0.00GB iome=7936.00MB iomp=16 ent=0.20

physb   hpi  hpit  pmem  iomin   iomu   iomf  iohwm iomaf %entc  vcsw
----- ----- ----- ----- ------ ------ ------ ------ ----- ----- -----
0.64     0     0  7.75   46.8   -     -     -       0   4.1 1250974887

            iompn: iomin  iodes   iomu  iores  iohwm  iomaf
       ent1.txpool  2.12  16.00   2.00   2.12   2.00      0
    ent1.rxpool__4  4.00  16.00   3.50   4.00   3.50      0
    ent1.rxpool__3  4.00  16.00   2.00  16.00   2.00      0
    ent1.rxpool__2  2.50   5.00   2.00   2.50   2.00      0
    ent1.rxpool__1  0.84   2.25   0.75   0.84   0.75      0
    ent1.rxpool__0  1.59   4.25   1.50   1.59   1.50      0
      ent1.phypmem  0.10   0.10   0.09   0.10   0.09      0
       ent0.txpool  2.12  16.00   2.00   2.12   2.00      0
    ent0.rxpool__4  4.00  16.00   3.50   4.00   3.50      0
    ent0.rxpool__3  4.00  16.00   2.00  16.00   2.00      0
    ent0.rxpool__2  2.50   5.00   2.00   2.50   2.00      0
    ent0.rxpool__1  0.84   2.25   0.75   0.84   0.75      0
    ent0.rxpool__0  1.59   4.25   1.50   1.59   1.50      0
      ent0.phypmem  0.10   0.10   0.09   0.10   0.09      0
            vscsi0 16.50  16.50   0.13  16.50   0.18      0
              sys0  0.00   0.00   0.00   0.00   0.00      0
'''
AIX_LPARSTATS_HYPERVISOR = '''

System configuration: type=Shared mode=Uncapped smt=On lcpu=4 mem=7936MB psize=16 ent=0.20

           Detailed information on Hypervisor Calls

Hypervisor                  Number of    %Total Time   %Hypervisor   Avg Call    Max Call
  Call                        Calls         Spent      Time Spent    Time(ns)    Time(ns)

remove                          15            0.0           0.4       1218        1781
read                             0            0.0           0.0          0           0
nclear_mod                       0            0.0           0.0          0           0
page_init                      316            0.0           9.7       1452        6843
clear_ref                        0            0.0           0.0          0           0
protect                          0            0.0           0.0          0           0
put_tce                          0            0.0           0.0          0           0
h_put_tce_indirect               0            0.0           0.0          0           0
xirr                            75            0.1           0.5       1823       10062
eoi                             73            0.0           0.3       1032        4437
ipi                              0            0.0           0.0          0           0
cppr                            40            0.0           0.1        690        3375
asr                              0            0.0           0.0          0           0
others                          91            0.1           1.2       3294       33906
cede                           354           11.9          95.1      67328    39936500
enter                           72            0.0           0.2        695        2531
migrate_dma                      0            0.0           0.0          0           0
put_rtce                         0            0.0           0.0          0           0
confer                           0            0.0           0.0          0           0
prod                             0            0.0           0.0          0        3843
get_ppp                          7            0.2           1.2      43901      107937
set_ppp                          0            0.0           0.0          0           0
purr                             0            0.0           0.0          0           0
pic                              7            0.0           0.0        517        3125
bulk_remove                      0            0.0           0.0          0        5187
send_crq                         1            0.0           0.0       8593        8593
copy_rdma                        0            0.0           0.0          0           0
get_tce                          0            0.0           0.0          0           0
send_logical_lan                 9            0.1           0.5      12809       34093
add_logical_lan_buf             81            0.1           0.7       2307        7625
h_remove_rtce                    0            0.0           0.0          0           0
h_ipoll                         20            0.0           0.0        459        2062
h_stuff_tce                      0            0.0           0.0          0           0
h_get_mpp                        0            0.0           0.0          0           0
h_get_mpp_x                      0            0.0           0.0          0           0
h_get_em_parms                   8            0.0           0.0        625        1656
h_vpm_pstat                      0            0.0           0.0          0           0
h_hfi_start_interface            0            0.0           0.0          0           0
h_hfi_stop_interface             0            0.0           0.0          0           0
h_hfi_query_interface            0            0.0           0.0          0           0
h_hfi_query_window               0            0.0           0.0          0           0
h_hfi_open_window                0            0.0           0.0          0           0
h_hfi_close_window               0            0.0           0.0          0           0
h_hfi_dump_info                  0            0.0           0.0          0           0
h_hfi_adapter_attach             0            0.0           0.0          0           0
h_hfi_modify_rcxt                0            0.0           0.0          0           0
h_hfi_route_info                 0            0.0           0.0          0           0
h_cau_write_index                0            0.0           0.0          0           0
h_cau_read_index                 0            0.0           0.0          0           0
h_nmmu_start                     0            0.0           0.0          0           0
h_nmmu_stop                      0            0.0           0.0          0           0
h_nmmu_allocate_resource         0            0.0           0.0          0           0
h_nmmu_free_resource             0            0.0           0.0          0           0
h_nmmu_modify_resource           0            0.0           0.0          0           0
h_confer_adjunct                 0            0.0           0.0          0           0
h_adjunct_mode                   0            0.0           0.0          0           0
h_get_ppp_x                      0            0.0           0.0          0           0
h_cop_op                         0            0.0           0.0          0           0
h_stop_cop_op                    0            0.0           0.0          0           0
h_random                         0            0.0           0.0          0           0
h_enter_decomp                   0            0.0           0.0          0           0
h_remove_comp                    0            0.0           0.0          0           0
h_xirr_x                         0            0.0           0.0          0           0
h_get_perf_info                  0            0.0           0.0          0           0
h_block_remove                   0            0.0           0.0          0           0
--------------------------------------------------------------------------------
'''
AIX_LPARSTATS_SPURR = '''

System configuration: type=Shared mode=Uncapped smt=On lcpu=4 mem=7936MB ent=0.20 Power=Disabled

Physical Processor Utilisation:

 --------Actual--------              ------Normalised------
 user   sys  wait  idle      freq    user   sys  wait  idle
 ----  ----  ----  ----   ---------  ----  ----  ----  ----
0.008 0.012 0.000 0.180 3.6GHz[100%] 0.008 0.012 0.000 0.180
'''


def collect_column(input, row_idx):
    collected = []
    for row in input:
        name = filter(None, row.split(' '))[row_idx]
        collected.append(name)

    return collected


@mock.patch("checks.corechecks.system.lparstats.get_subprocess_output", return_value=(AIX_LPARSTATS_MEMORY, None, None))
def test_memory(get_subprocess_output):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = lparstats.LPARStats("lparstats", {}, {}, aggregator)
    c.collect_memory(page_stats=False)
    metrics = c.aggregator.flush()

    # NOTE: iomu, iomf, iohwm unavailable
    expected_metrics = [
        'system.lpar.memory.physb',
        'system.lpar.memory.hpi',
        'system.lpar.memory.hpit',
        'system.lpar.memory.pmem',
        'system.lpar.memory.iomin',
        'system.lpar.memory.iomaf',
        'system.lpar.memory.entc',
        'system.lpar.memory.vcsw',
    ]

    # # we subtract two - one for /proc, and one for the heading
    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics


@mock.patch("checks.corechecks.system.lparstats.get_subprocess_output", return_value=(AIX_LPARSTATS_MEMORY_PAGE, None, None))
def test_memory_page(get_subprocess_output):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = lparstats.LPARStats("lparstats", {}, {}, aggregator)
    c.collect_memory(page_stats=True)
    metrics = c.aggregator.flush()

    # NOTE: iomf unavailable
    expected_metrics = [
        'system.lpar.memory.physb',
        'system.lpar.memory.hpi',
        'system.lpar.memory.hpit',
        'system.lpar.memory.pmem',
        'system.lpar.memory.iomu',
        'system.lpar.memory.iomin',
        'system.lpar.memory.iohwm',
        'system.lpar.memory.iomaf',
        'system.lpar.memory.pgcol',
        'system.lpar.memory.mpgcol',
        'system.lpar.memory.ccol',
        'system.lpar.memory.entc',
        'system.lpar.memory.vcsw',
    ]

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics


@mock.patch("checks.corechecks.system.lparstats.get_subprocess_output", return_value=(AIX_LPARSTATS_MEMORY_ENTITLEMENTS, None, None))
def test_memory_entitlements(get_subprocess_output):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = lparstats.LPARStats("lparstats", {}, {}, aggregator)
    c.collect_memory_entitlements()
    metrics = c.aggregator.flush()

    expected_metrics = [
        'system.lpar.memory.entitlement.iomin',
        'system.lpar.memory.entitlement.iodes',
        'system.lpar.memory.entitlement.iomu',
        'system.lpar.memory.entitlement.iores',
        'system.lpar.memory.entitlement.iohwm',
        'system.lpar.memory.entitlement.iomaf',
    ]

    # compile entitlements from mock output
    output = filter(None, AIX_LPARSTATS_MEMORY_ENTITLEMENTS.splitlines())
    output = output[c.MEMORY_ENTITLEMENTS_START_IDX + 1:]
    entitlements = collect_column(output, 0)

    assert len(metrics) == (len(expected_metrics) * len(entitlements))
    for metric in metrics:
        for tag in metric['tags']:
            if 'iompn' in tag:
                assert tag.split(':')[1] in entitlements


@mock.patch("checks.corechecks.system.lparstats.get_subprocess_output", return_value=(AIX_LPARSTATS_HYPERVISOR, None, None))
def test_hypervisor(get_subprocess_output):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = lparstats.LPARStats("lparstats", {}, {}, aggregator)
    c.collect_hypervisor()
    metrics = c.aggregator.flush()

    # compile hypervisor calls from mock output
    output = filter(None, AIX_LPARSTATS_HYPERVISOR.splitlines())
    output = output[c.HYPERVISOR_METRICS_START_IDX:-1]
    calls = collect_column(output, 0)

    assert len(metrics) == (len(c.HYPERVISOR_IDX_METRIC_MAP) * len(calls))
    for metric in metrics:
        assert metric['metric'] in c.HYPERVISOR_IDX_METRIC_MAP.values()
        for tag in metric['tags']:
            if 'call' in tag:
                assert tag.split(':')[1] in calls


@mock.patch("checks.corechecks.system.lparstats.get_subprocess_output", return_value=(AIX_LPARSTATS_SPURR, None, None))
def test_spurr(get_subprocess_output):

    hostname = 'foo'
    aggregator = MetricsAggregator(
        hostname,
        interval=1.0,
        histogram_aggregates=None,
        histogram_percentiles=None,
    )

    c = lparstats.LPARStats("lparstats", {}, {}, aggregator)
    c.collect_spurr()
    metrics = c.aggregator.flush()

    expected_metrics = [
        'system.lpar.spurr.user',
        'system.lpar.spurr.sys',
        'system.lpar.spurr.wait',
        'system.lpar.spurr.idle',
        'system.lpar.spurr.user.norm',
        'system.lpar.spurr.sys.norm',
        'system.lpar.spurr.wait.norm',
        'system.lpar.spurr.idle.norm',
        'system.lpar.spurr.user.pct',
        'system.lpar.spurr.sys.pct',
        'system.lpar.spurr.wait.pct',
        'system.lpar.spurr.idle.pct',
        'system.lpar.spurr.user.norm.pct',
        'system.lpar.spurr.sys.norm.pct',
        'system.lpar.spurr.wait.norm.pct',
        'system.lpar.spurr.idle.norm.pct',
    ]

    assert len(metrics) == len(expected_metrics)
    for metric in metrics:
        assert metric['metric'] in expected_metrics
