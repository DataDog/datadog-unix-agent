Release Notes
=============

1.0.0
-----

Released on: <unreleased> 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* stable


0.10.0 (dev release)
--------------------

Released on: 2019-02-14 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* Aggregator: fix regression
* Config: use correct site location for Flare, API endpoints too
* Installer: adding proxy support to 1-step script
* Logging: consistent message formatting
* Packaging: address PYC file cleanup bug

0.9.1 (dev release)
--------------------

Released on: 2019-02-14 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* Network: re-adding network check 
* Config: multiple configuration file cleanup
* Logging: improved levels, messages 

0.9.0 (dev release)
--------------------

Released on: 2019-02-14 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* Config: add site support
* Dogstatsd: allow running dogstatsd embedded in agent process
* Dogstatsd: track process running standalone 
* Dogstatsd: compute basic statistics  
* Dogstatsd: fix python3 bug - default to utf-8 encoding  
* Flare: send agent version and platform with flare meta
* Installer: adding 1-step installer script
* Status: multiple improvements

0.8.1 (dev release)
--------------------

Released on: 2019-02-14 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* Status: Adding datadog-agent status page
* Flare: ship status with flare
* Flare: address submission bug
* Flare: redact log, config file contents 
* Config: load checks in correct order
* Packaging: ship pyc files, cleanup old bytecode 

0.8.0 (dev release)
--------------------

Released on: 2019-03-22 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* Network: Adding Check
* Disk: Adding Check
* CPU: Adding more supported metrics
* LPARStats: Adding sudo support 
* Aggregator: Compute statistics
* Config: fix configuration path overrides
* Config: self-contained reload when using env vars. 
* Metadata: fix payload format bug, and send perodically
* Utils: add sudo support for subprocess command execution

0.7.1 (dev release)
--------------------

Released on: 2019-02-14 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* Improved configurability of API server listening address/port.


0.7.0 (dev release)
--------------------

Released on: 2019-02-13 

Supported Platforms:
* AIX 6.1 / 7.1 / 7.2

### Details 

* Agent runs on Python3.
* Agent runs as an SRC subsystem on AIX.
* Agent installs to typical datadog agent locations:
  * /opt/datadog-agent
  * /etc/datadog-agent
  * /var/log/datadog
* Agent starts automatically on start-up and will be respawned on AIX.
* Agent run by unprivileged `dd-agent` user on AIX.
* AIX-specific LPARstats check now ships as a bundled integration.
* Forwarder: improved resilience to submission/unexpected failures.
* Signal Management: improved multi-platform management of signals.

### Notes

* We recommend you remove previous versions before proceeding with
version `0.7.0`:
  * backup any relevant configurations
  * stop the running agent:
    1. `/opt/datadog-agent/agent/agent.py stop`
    2. `kill -9 <pid>` (unfortunately this will not be graceful).
  * uninstall with: `installp -u datadog-unix agent` 

