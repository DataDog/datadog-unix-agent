# Datadog Unix Agent

A Datadog Agent specifically designed for Unix-based systems.

Note: This agent has been designed with portability in mind but has only been tested at the
time of this writing on AIX.
If you have any questions, please contact our [support team](https://docs.datadoghq.com/help/).

The goal of this agent is to provide support for miscellaneous Unix operating systems not supported
by our currently available agents. To do so, it has been stripped of unnecessary bloat and cut around
less relevant use-cases given the target platforms. Only a subset of key and OS-specific features have
been implemented, please do not expect feature parity.

## AIX

### Omnibus Build

An omnibus build is available for the agent. The omnibus build provides a self-contained
environment, shipping all required dependencies, including python3 and other depending shared
objects. The omnibus build will however depend on a small subset of system-level dependencies
expected to be present on any AIX LPAR image; namely: libc, libpthreads, libdl and libcrypy.

Unfortunately, disparities exist between some of the system libs available symbols across AIX
technology levels on the *same* AIX version. This is an AIX particularity and means that we can
only guarantee the agent will run successfully on machines matching our builders' technology
level. That is:

#### Target Platforms

The omnibus build has been build and tested on the target platforms at the time of this writing:

- AIX 6.1 TL9 SP6
- AIX 7.1 TL5 SP3
- AIX 7.2 TL3 SP0
- AIX 7.3 TL3 SP0

Should you attempt to install and run the agent package on a lesser version your mileage will
vary, you may or may not have all required symbols available. We are working to improve our
support across al target platforms.

#### Omnibus Bootstrap

To help with the setup of the omnibus builder we have a (still a bit flaky ;) script that should
help you get up and building in a jiffy or two. It's a basic shell script located in the `omnibus/`
folder that will help you install, amongst others:
- YUM (rpm package manager)
- Required build toolchain (gcc, libffi, ...)
- Ruby
- Required tools (sudo, GNU tar, bundler)
- Patch required `libyajl-gem`

#### Build Baseline Requirements

The omnibus build now ships all these dependencies, most notably openssl and python, all properly
linked and only requiring AIX baseline system level dependencies expected to be available:
- libc
- libpthreads
- libcrypt
- libdl

#### Build Runtime Requirements

As mentioned above all requirements are bundled with the omnibus installer. For more details take
a look at the `omnibus/` directory to take a look at the implementation.

### Installation

Download links for the latest releases can be found [on this page](https://github.com/DataDog/datadog-unix-agent/releases).

The installer may be executed as follows (as root):

```bash
installp -aXYgd ./datadog-unix-agent-<version>.powerpc.bff -e dd-aix-install.log datadog-unix-agent
```

This will install the agent in `/opt/datadog-agent`.

Note how we're logging to `dd-aix-install.log`, you may skip that by removing the `-e` switch.

#### Running the agent

The expected configuration location is:
```
/etc/datadog-agent/datadog.yaml
```

That said, config file will be searched in this order (with the first match being
taken):
- `/etc/datadog-agent/datadog.yaml`
- `./etc/datadog-agent/datadog.yaml`
- `./datadog.yaml`

This should support legacy configuration locations from early adopters who may have
installed earlier dev images. Please try to update to the preferred location to avoid
issues in the future with potential deprecations.

A sample configuration file may be found in `/etc/datadog-agent/datadog.yaml.example`.

A basic configuration will typically require your datadog API key. Should you require
to submit your metrics to the EU instance, the `site` configuration option is available.
You may also override the `dd_url` manually, but that should not be required.

Occassionally a proxy configuration must be specified depending on your network setup.

In versions `>=0.7.0`, an SRC subsystem is created so you can now manage the agent
using the usual AIX commands to manage it. Thus, with the configuration in place,
you may start the agent with:
```bash
startsrc -s datadog-agent
```

You may check the status with:
```bash
lssrc -s datadog-agent
```

And you may stop it with:
```bash
stopsrc -s datadog-agent
```

Please note that an `inittab` entry is now created automatically on package installation
and the agent will be brought up automatically when runlevel 2 is entered. If you wish
to disable this behavior please run the corresponding `rmitab` command:
```bash
rmitab "datadog-agent"
```

The default `inittab` configuration enables the service in `respawn` mode, such that if
the agent should crash, it will be automatically respawned. The goal of this behavior
is to help avoid a loss in observability in the event of an agent crash. AIX service
management is a little rudimentary, so if this behavior is too invasive for your liking
you may change the behavior from `respawn` to `once`:
```bash
chitab "datadog-agent:2:once:/usr/bin/startsrc -s datadog-agent"
```

**Note: in this scenario the agent will not be automatically restarted in the event of
a crash.**

##### Deprecated

The following instructions refer only to earlier iterations of this project and do not
apply to the `stable` agent (1.0.0) or dev versions `>=0.7.0`. These are here for historic
reference.

With older versions of the agent, you will have to resort to the manual start procedure
for the agent daemon:

```bash
/opt/datadog-agent/agent/agent.py -b start
```

As well as the manual call to stop it:
```bash
/opt/datadog-agent/agent/agent.py stop
```

If you want to run the agent in the foreground, please omit the `-b` switch.

If you wish to override any configuration setting defined in the config file, you
may resort to environment variables as follows:
```bash
DD_LOG_LEVEL=debug ./agent.py start
```

#### Running dogstatsd

Dogstatsd allows collecting and submitting custom metrics to datadog. It listens on
a UDP port and statsd metrics may be submitted to it. These will then be relayed
to Datadog.

Dogstatsd relies on the same configuration file defined for the agent where a `dogstatsd`
configuration section is available. The dogstatsd server will typically run within the
same agent process, but should you need a dedicated process it may also be launched in
standalone mode.

To enable dogstatsd, simply edit `/etc/datadog-agent/datadog.yaml` and set the relevant
configuration options.

```yaml
dogstatsd:                        # Dogstatsd configuration options
  enabled: true                   # disabled by default
  bind_host: localhost            # address we'll be binding to
  port: 8125                      # dogstatsd UDP listening port
  non_local_traffic: false        # listen to non-local traffic
```

### Integrations

#### System Integrations

The following system-level integrations are enabled by default:

 - CPU
 - Filesystem
 - IOStat
 - Load
 - Memory
 - Uptime

#### Bundled Integrations

Additional integrations currently available:
 - Disk
 - LPARstats
 - Network 
 - Process

For bundled integrations, a configuration file should be put in place to enable
the integration. Some of these, like the network check, might already be enabled
by default. These configuration files should be found in `./etc/datadog-agent/conf.d`.
The name of the YAML configuration file should match that of the integration:
`./etc/datadog-agent/conf.d/foo.yaml` will enable integration `foo`, and set its
configuration.

If changes are made to an agent integration, the agent will have to be restarted,
configuration changes are not picked up automatically.

These integrations are shipped as python wheels. You may develop your own should
yout need to, all you have to do is follow the blueprint set by the bundled wheels
[here](https://github.com/DataDog/datadog-unix-agent/tree/master/checks/bundled).

See more in the developer notes [here](#integrations).

### Uninstall
To remove an installed agent you will run a similar `installp` command:
```
installp -e dd-aix-uninstall.log -uv datadog-unix-agent
```
Note how we're again logging to `dd-aix-install.log`, you may skip that by removing the `-e` switch.

#### Removing Older Agents

##### Deprecated

The following instructions should only apply to early adopters who may have installed
early `dev` versions of the unix agent. The following does **NOT** apply to agent installs
that used the BFF package. Kept here for historic reference.

If you had used the previous scripted installer to install a previous early-development version of the
agent, the former location was `/opt/datadog/datadog-unix-agent`, you will have to remove that manually.
Please be mindful to preserve you configurations from that setup if you wish to reuse them with the new
agent. You can use the same files, and drop them into the same relative paths in `/opt/datadog-agent`.

The reason the location was modified was to provide a consistent location across agent versions and
platforms, to match the user experience in Agent 5 and Agent 6.

This should allow you to disable the old running agent and safely delete the old location:

```bash
cd /opt/datadog/datadog-unix-agent
. ./venv/bin/activate
./agent.py stop
deactivate
cd ~
# remember to backup config files if required
rm -rf /opt/datadog/datadog-unix-agent
```

RPM dependencies installed by the scripted installer are no longer required and may be removed if you
so wish. This is the list of former RPM requirements:
- ca-certificates-2016.10.7-2.aix6.1.ppc.rpm
- curl-7.52.1-1.aix6.1.ppc.rpm
- db-4.8.24-3.aix6.1.ppc.rpm
- gdbm-1.8.3-5.aix5.2.ppc.rpm
- gettext-0.19.7-1.aix6.1.ppc.rpm
- glib2-2.14.6-2.aix5.2.ppc.rpm
- python-2.7.10-1.aix6.1.ppc.rpm
- python-devel-2.7.10-1.aix6.1.ppc.rpm
- python-iniparse-0.4-1.aix6.1.noarch.rpm
- python-pycurl-7.19.3-1.aix6.1.ppc.rpm
- python-tools-2.7.10-1.aix6.1.ppc.rpm
- python-urlgrabber-3.10.1-1.aix6.1.noarch.rpm
- readline-6.1-2.aix6.1.ppc.rpm


## Developer Notes

The agent runs on Python3.  You will typically want `setuptools`, `wheel` and `virtualenv`
on your python development environment. We also have some development tools requirements,
you may install them with:
```bash
pip install -r requirements-dev.txt
```

You may mostly work on this repo from any \*nix environment. We do have some python
binary wheel dependencies, on linux these are typically provided as `manylinux`
pre-built wheels so just installing the requirements should work. Other platforms
(like macOS) might also have pre-built wheels. And in the more popular environments,
even if compiled wheels are not available, building the wheels during the pip
installation should be seamless.

```bash
pip install -r requirements.txt
```

### Building

#### Omnibus build

This is the recommended way for building the agent. Hopefully setting up omnibus on
the builder will be scripted, but until then getting the builder ready is a manual
process.

##### Platforms
You will need a build machine that matches the target platform, thus:
- AIX 6.1
- AIX 7.1
- AIX 7.2
- AIX 7.3

##### Omnibus Requirements
To setup omnibus on the target machine you will need:
- [AIX Linux toolkit](https://www.ibm.com/developerworks/aix/library/aix-toolbox/alpha.html)
- `gcc` (>= 6.3.0 via yum)
- `coreutils` (via yum - provided with the linux toolkit)
- `sudo` (via yum)
- `libffi` and `libffi-devel` (via yum): required to bootstrap ruby.
- `ruby` and `ruby-devel` (via yum)
- GNU `tar` (via yum)
- `bundler` (via `gem install bundler`)

Now let's install the omnibus dependencies, navigate to `omnibus/`:

- `bundle install`: when the bundle get to `libyajl` it will fail on AIX, don't worry we
have a workaround. Please read on.

On AIX You will need to install a modified version of libyajl before proceeding (you can
run these commands in a scratch directory somewhere):
- [`libyajl2-gem`](https://github.com/truthbk/libyajl2-gem) @ branch `jaime/aix`
  - [yajl](https://github.com/lloyd/yajl/tree/12ee82ae5138ac86252c41f3ae8f9fd9880e4284):
  you will have to check `yajl` out in this location `libyajl2-gem/ext/libyajl/vendor/yajl`
- `bundle install`
- `rake prep`
- `rake gem`
- `gem install --local ./pkg/libyajl-1.2.0.gem`

Once these steps are complete, you may go back to `omnibus/` in the agent repo and run
`bundle install` or `bundle update` once again.

If you got here you're doing good and you're almost ready to go.

##### Build Runtime Requirements + Troubleshooting

- Make sure the ulimits are high enough if you receive out of memory errors (check them with `ulimit -a`):
  - `ulimit -m unlimited` (for `max memory size`)
  - `ulimit -s unlimited` (for `stack size`)
  - `ulimit -d unlimited` (for `data seg size`)
- Make sure you have enough space in `/opt` for the requirements + build. (check with `df -m`, increase with `chfs -a size=+2G /opt`)
- Make sure you have enough space in `/var` for the omnibus build
- Omnibus uses git, make sure you have configured git username, etc.
- If you have issues installing `gcc` 6.3.0, you might need to manually remove `gcc-locale`
before attempting the upgrade if `gcc` is already installed on your system..
- Set the `PATH`: `export PATH="/opt/freeware/bin:$PATH"`
- Set the `CONFIG_SHELL`: `export CONFIG_SHELL="/bin/bash"`
- Set the `TERM`: for convenience `export TERM=xterm`


*Note*: please note that the `omnibus-ruby` installer currently requires the `datadog-5.5.0-aix`
branch on AIX. That will probably be merged to `master`, but currently is required. No need
for the developer to do anything as that specific branch is the current default for AIX builds.

*Note*: You can override `omnibus-ruby` gem version if necessary with
the `OMNIBUS_RUBY_VERSION` variable - followed by a `bundle update`.

#### Building

Triggering a build is the easiest part, typically:
```
bundle exec omnibus build agent --log-level=info
```

### Integrations

The agent has two types of checks or integrations.
  - Core checks: built into the agent.
  - Wheel checks: additional integrations we may package, bundle and install on an
  agent environment.

Here, we will mostly discuss wheel checks, as they provide the natural facilities to
extend the agent.

All checks (both core and whell) depend on the AgentCheck base class, shipped in the
project's `checks.agent_check` module, and will inherit from it. This base class will
ship with the agent and can be considered part of the environment, wheel checks can
expect its availability.

The pattern for the wheel checks has been taken from [integrations-core](https://docs.datadoghq.com/developers/integrations/),
so if you're familiar with that, you should be able to hit the ground running.

A check wheel `foo` should have the following skeleton:

```
checks/bundled/foo/README.md                                    # check README.
checks/bundled/foo/setup.py                                     # python package setup.
checks/bundled/foo/tests/                                       # tests - we use pytest.
checks/bundled/foo/datadog_checks/__init__.py                   # namespace module init - note: this file is not shipped with the wheel. 
checks/bundled/foo/datadog_checks/foo/__about__.py              # foo module about - includes version info.
checks/bundled/foo/datadog_checks/foo/__init__.py               # foo module init.
checks/bundled/foo/datadog_checks/foo/foo.py                    # foo check implementation.
checks/bundled/foo/datadog_checks/foo/data/conf.yaml.example    # sample configuration.
checks/bundled/foo/pytest.ini                                   # any additional pytest config.
checks/bundled/foo/requirements-dev.txt                         # (optional) any additional dev requirements.
```

Please take a look at any of the bundled checks [here](https://github.com/DataDog/datadog-unix-agent/tree/master/checks/bundled)
for inspiration.

_Note:_ JMXFetch is included in the build but is not officially supported (the AIX Agent does not
include the facilities to configure and start JMXFetch).

