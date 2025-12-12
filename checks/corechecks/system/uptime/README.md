# Uptime Check

## Overview

The Uptime check reports the system uptime in seconds.  
It uses the `python-uptime` library when available, and falls back to parsing the elapsed time of PID 1 when necessary.  
This ensures uptime reporting works consistently across AIX and other Unix platforms.

## Setup

### Installation

The Uptime check is included in the Datadog Unix Agent package.

### Configuration

A configuration file is not required.  
You may optionally provide tags in `uptime.d/conf.yaml`.

To disable the check:

```bash
CONF_PATH=/etc/datadog-agent/conf.d/
mv $CONF_PATH/uptime.d/conf.yaml.default $CONF_PATH/uptime.d/conf.yaml.default.disabled
```

## Validation

Run [`datadog-agent status`][1] and look for `uptime` under the Checks section.

## Data Collected

### Metrics

| metric_name   | metric_type | unit_name | description                              |
| ------------- | ----------- | --------- | ---------------------------------------- |
| system.uptime | gauge       |           | Total system uptime reported in seconds. |

### Events

This check does not report events.

### Service Checks

This check does not include service checks.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[2]: https://docs.datadoghq.com/help/
