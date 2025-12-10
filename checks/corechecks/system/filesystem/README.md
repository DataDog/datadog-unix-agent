# Filesystem Check

## Overview

The Filesystem check reports per-mountpoint disk usage.  
Metrics include total, used, and available space in mebibytes (MiB), along with percentage available.

## Setup

### Installation

The Filesystem check is included in the Datadog Agent package.

### Configuration

A configuration file is not required.  
You may optionally provide tags in `filesystem.d/conf.yaml`.

To disable the check:

```bash
CONF_PATH=/etc/datadog-agent/conf.d/
mv $CONF_PATH/filesystem.d/conf.yaml.default $CONF_PATH/filesystem.d/conf.yaml.default.disabled
```

## Validation

Run [`datadog-agent status`][1] and look for `filesystem` under the Checks section.

## Data Collected

### Metrics

| metric_name             | metric_type | unit_name | description                       |
| ----------------------- | ----------- | --------- | --------------------------------- |
| system.fs.total         | gauge       |           | Total filesystem size (MiB).      |
| system.fs.used          | gauge       |           | Used filesystem space (MiB).      |
| system.fs.available     | gauge       |           | Available filesystem space (MiB). |
| system.fs.available.pct | gauge       |           | Percentage of available space.    |

### Events

This check does not report events.

### Service Checks

This check does not include service checks.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[2]: https://docs.datadoghq.com/help/

