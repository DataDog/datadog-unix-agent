# CPU Check

## Overview

The CPU check reports per-core CPU usage percentages using system APIs.  
Each metric includes a `core:<id>` tag to identify the originating CPU core.

## Setup

### Installation

The CPU check is included in the Datadog Agent package.

### Configuration

A configuration file is not required.  
You may optionally provide tags in `cpu.d/conf.yaml`.

To disable the check:

```bash
CONF_PATH=/etc/datadog-agent/conf.d/
mv $CONF_PATH/cpu.d/conf.yaml.default $CONF_PATH/cpu.d/conf.yaml.default.disabled
```

## Validation

Run [`datadog-agent status`][1] and look for `cpu` under the Checks section.

## Data Collected

### Metrics

| metric_name           | metric_type | unit_name | description                                |
| --------------------- | ----------- | --------- | ------------------------------------------ |
| system.cpu.user       | gauge       |           | Time spent in user mode.                   |
| system.cpu.system     | gauge       |           | Time spent in kernel mode.                 |
| system.cpu.idle       | gauge       |           | Idle CPU time.                             |
| system.cpu.iowait     | gauge       |           | Time spent waiting on I/O.                 |
| system.cpu.nice       | gauge       |           | Time spent running low-priority processes. |
| system.cpu.irq        | gauge       |           | Time servicing hardware interrupts.        |
| system.cpu.softirq    | gauge       |           | Time servicing software interrupts.        |
| system.cpu.steal      | gauge       |           | Time stolen by the hypervisor.             |
| system.cpu.guest      | gauge       |           | Time running guest OS code.                |
| system.cpu.guest_nice | gauge       |           | Guest time at low priority.                |

### Events

This check does not report events.

### Service Checks

This check does not include service checks.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[2]: https://docs.datadoghq.com/help/


