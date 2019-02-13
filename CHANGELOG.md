Release Notes
=============

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

