# IOStat Check

## Overview

The IOStat check parses AIX `iostat -Dsal` output and reports block device performance metrics.  
It emits transfer rates, service times, queue statistics, and identifier tags for physical, virtual, and logical devices.

## Setup

### Installation

The IOStat check is included in the Datadog Unix Agent package.

### Configuration

A configuration file is not required.

To disable the check:

```bash
CONF_PATH=/etc/datadog-agent/conf.d/
mv $CONF_PATH/iostat.d/conf.yaml.default $CONF_PATH/iostat.d/conf.yaml.default.disabled
```

## Validation

Run [`datadog-agent status`][1] and look for `iostat` under the Checks section.

## Data Collected

### Metrics

Metrics follow the pattern:

```
system.iostat.<mode>.<section>.<column>
```

Example metrics include:

| metric_name                             | metric_type | unit_name | description                 |
| --------------------------------------- | ----------- | --------- | --------------------------- |
| system.iostat.physical.kbps             | gauge       |           | Kilobytes per second.       |
| system.iostat.physical.tps              | gauge       |           | Transfers per second.       |
| system.iostat.vadapter.xfers.blks.read  | gauge       |           | Blocks read.                |
| system.iostat.vadapter.xfers.blks.write | gauge       |           | Blocks written.             |
| system.iostat.vadapter.read.rps         | gauge       |           | Reads per second.           |
| system.iostat.vadapter.read.serv.avg    | gauge       |           | Average read service time.  |
| system.iostat.disks.queue.wqsz.avg      | gauge       |           | Average write queue size.   |
| system.iostat.disks.queue.sqsz.avg      | gauge       |           | Average service queue size. |

Additional metrics are emitted according to the IOStat schema defined in the check.

### Events

This check does not report events.

### Service Checks

This check does not include service checks.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[2]: https://docs.datadoghq.com/help/
