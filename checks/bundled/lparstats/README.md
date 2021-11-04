# LPARstats Check

## Overview

The LPARstats check lets you:

* Collect resource usage metrics for detailed LPAR metrics on any host
* Use [LPARstats Monitors][1]: configure thresholds for how many instances of a specific process ought to be running and get alerts when the thresholds aren't met (see **Service Checks** below).

## Setup

### Installation

The lparstats check is included in the Agent package, so you don't need to install anything else on your server.

### Configuration

* Create /etc/datadog-agent/conf.d/lparstats.d/conf.yaml with the contents:
```
init_config:
instances:
  - name: lparstats
    sudo: true
```
* Edit /etc/sudoers and add this at the end:
```
dd-agent ALL=(ALL) NOPASSWD: /usr/bin/lparstat
```

### Validation

Run the Agent's status subcommand and look for `lparstats` under the Checks section.

## Data Collected
### Metrics
TODO

### Events
TODO

### Service Checks
TODO

## Troubleshooting
TODO

## Further Reading
TODO
