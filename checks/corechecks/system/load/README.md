# Load Check

## Overview

The Load check reports the system’s 1-, 5-, and 15-minute load averages.  
It also reports normalized load (load divided by the number of CPU cores).  
On AIX systems where load averages are unavailable, the check falls back to parsing the `uptime` command output.

## Setup

### Installation

The Load check is included in the Datadog Unix Agent package.

### Configuration

A configuration file is not required.  
You may optionally provide tags in `load.d/conf.yaml`.

To disable the check:

```bash
CONF_PATH=/etc/datadog-agent/conf.d/
mv $CONF_PATH/load.d/conf.yaml.default $CONF_PATH/load.d/conf.yaml.default.disabled
```

## Validation

Run [`datadog-agent status`][1] and look for `load` under the Checks section.

## Data Collected

### Metrics

| metric_name         | metric_type | unit_name | description                              |
| ------------------- | ----------- | --------- | ---------------------------------------- |
| system.load.1       | gauge       |           | 1-minute load average.                   |
| system.load.5       | gauge       |           | 5-minute load average.                   |
| system.load.15      | gauge       |           | 15-minute load average.                  |
| system.load.norm.1  | gauge       |           | Normalized 1-minute load (load ÷ cores). |
| system.load.norm.5  | gauge       |           | Normalized 5-minute load.                |
| system.load.norm.15 | gauge       |           | Normalized 15-minute load.               |

### Events

This check does not report events.

### Service Checks

This check does not include service checks.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[2]: https://docs.datadoghq.com/help/

