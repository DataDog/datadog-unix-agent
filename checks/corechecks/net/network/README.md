# Network Check

## Overview

The network check lets you:

* Collect resource usage metrics for network on the target host, including: network usage, I/O counters, etc

## Setup
### Installation

The network check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

The network check is enabled by default, and the Agent collects metrics on all network interfaces.
If you want to configure the check with custom options, edit the `network.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample network.d/conf.yaml][3] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][4] and look for `network` under the Checks section.

## Data Collected

### Metrics

| metric_name                  | metric_type | unit_name | description                  |
| ---------------------------- | ----------- | --------- | ---------------------------- |
| system.net.bytes_sent        | gauge       |           | Number of bytes sent.        |
| system.net.bytes_rcvd        | gauge       |           | Number of bytes received.    |
| system.net.packets_in.count  | gauge       |           | Incoming packets.            |
| system.net.packets_out.count | gauge       |           | Outgoing packets.            |
| system.net.packets_in.error  | gauge       |           | Incoming packet errors.      |
| system.net.packets_out.error | gauge       |           | Outgoing packet errors.      |
| system.net.packets_in.drop   | gauge       |           | Incoming dropped packets.    |
| system.net.packets_out.drop  | gauge       |           | Outgoing dropped packets.    |

### Events

The network check does not include any events.

### Service Checks

The network check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://app.datadoghq.com/account/settings#agent  
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory  
[3]: https://github.com/DataDog/integrations-core/blob/master/network/datadog_checks/network/data/conf.yaml.default  
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information  
[5]: https://github.com/DataDog/integrations-core/blob/master/network/metadata.csv  
[6]: https://docs.datadoghq.com/help
