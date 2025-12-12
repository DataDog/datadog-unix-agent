# Memory Check

## Overview

The Memory check reports system memory and swap usage.  
Metrics include total, free, used, and available memory expressed in mebibytes (MiB), along with percentage-based gauges.

## Setup

### Installation

The Memory check is included in the Datadog Unix Agent package.

### Configuration

A configuration file is not required.  
You may optionally provide tags in `memory.d/conf.yaml`.

To disable the check:

```bash
CONF_PATH=/etc/datadog-agent/conf.d/
mv $CONF_PATH/memory.d/conf.yaml.default $CONF_PATH/memory.d/conf.yaml.default.disabled
```

## Validation

Run [`datadog-agent status`][1] and look for `memory` under the Checks section.

## Data Collected

### Metrics

| metric_name           | metric_type | unit_name | description                              |
| --------------------- | ----------- | --------- | ---------------------------------------- |
| system.mem.total      | gauge       |           | Total system memory (MiB).               |
| system.mem.free       | gauge       |           | Free system memory (MiB).                |
| system.mem.used       | gauge       |           | Used system memory (MiB).                |
| system.mem.usable     | gauge       |           | Available memory (MiB).                  |
| system.mem.pct_usable | gauge       |           | Fraction of total memory that is usable. |
| system.swap.total     | gauge       |           | Total swap space (MiB).                  |
| system.swap.free      | gauge       |           | Free swap space (MiB).                   |
| system.swap.used      | gauge       |           | Used swap space (MiB).                   |
| system.swap.pct_free  | gauge       |           | Percentage of swap space that is free.   |

### Events

This check does not report events.

### Service Checks

This check does not include service checks.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[2]: https://docs.datadoghq.com/help/
