# Agent Check: IBM WAS

## Overview

This check monitors [IBM Websphere Application Server (WAS)][1] through the Datadog Agent. This check supports IBM WAS versions >= 8.5.5.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

The IBM WAS Datadog integration collects enabled PMI Counters from the WebSphere Application Server environment. Setup requires enabling the PerfServlet, which provides a way for Datadog to retrieve performance data from WAS.

By default, this check collects JDBC, JVM, thread pool, and Servlet Session Manager metrics. You may optionally specify additional metrics to collect in the "custom_queries" section. See the [sample check configuration][3] for examples.

### Installation

The IBM WAS check is included in the [Datadog Agent][4] package.

#### Enable the `PerfServlet`

The servlet's .ear file (PerfServletApp.ear) is located in the `<WAS_HOME>/installableApps` directory, where `<WAS_HOME>` is the installation path for WebSphere Application Server.

The performance servlet is deployed exactly as any other servlet. Deploy the servlet on a single application server instance within the domain.

**Note**: Starting with version 6.1, you must enable application security to get the PerfServlet working.

### Modify the currently monitored statistic set

By default, your application server is only configured for "Basic" monitoring. In order to gain complete visibility into your JVM, JDBC connections, and servlet connections, change the currently monitored statistic set for your application server from "Basic" to "All".

From the Websphere Administration Console, you can find this setting in `Application servers > <YOUR_APP_SERVER> > Performance Monitoring Infrastructure (PMI)`.

Once you've made this change, click "Apply" to save the configuration and restart your application server. Additional JDBC, JVM, and servlet metrics should appear in Datadog shortly after this change.

### Configuration

1. Edit the `ibm_was.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to collect your IBM WAS performance data. See the [sample ibm_was.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][7] and look for `ibm_was` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

IBM WAS does not include any events.

### Service Checks

See [service_checks.json][10] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://www.ibm.com/cloud/websphere-application-platform
[3]: https://github.com/DataDog/datadog-unix-agent/blob/master/checks/bundled/ibm_was/datadog_checks/ibm_was/data/conf.yaml.example
[4]: https://app.datadoghq.com/account/settings#agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://github.com/DataDog/integrations-core/blob/master/ibm_was/assets/service_checks.json
