# Datadog Unix Agent

#### NOTE: This agent and all artifacts made available are still in early development.

A Datadog Agent specifically designed for Unix-based systems.

Note: This agent is currently in development for AIX. It has not been tested on other systems. If
you have any questions, please contact our [support team](https://docs.datadoghq.com/help/).

This agent targets miscellaneous Unix operating systems not supported by our currently available
agents. To do so, it has been stripped of unnecessary bloat and cut around irrelevant use-cases
given the target platforms, sometimes at the expense of certain features. To maximize portability
the agent will attempt to reduce the number of non pure-python dependencies to a minimum, and rely
on packages with native support for the targeted operating systems (currently AIX).

## AIX

### Omnibus Build

An omnibus build is now available for the agent. The omnibus build provides a self-contained
environment aiming to address the short-comings of previous approaches where we attempted to
provide dependencies externally. That approach proved error-prone since we always respected
packages already available in target LPARs to avoid risking breaking the system. Unfortuantely,
installed libraries could be potentially outdated or incompatible with the actual requirements.

Although we have been able to successfully test the agent in those platforms the omnibus build
is in its earliest iteration and some issues could surface given the wide disparity between LPAR
images. These issues are not expected but may occur due to the early maturity of this new build.

#### Target Platforms

The omnibus build has been tested on the target platforms:
- AIX 6.1
- AIX 7.1
- AIX 7.2

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

As of `0.7.0` the expected configuration location is:
```
/etc/datadog-agent/datadog.yaml
```

That said, config file will be searched in this order (with the first match being
taken):
- `/etc/datadog-agent/datadog.yaml`
- `./etc/datadog-agent/datadog.yaml`
- `./datadog.yaml`

This should support legacy configuration locations, but please try to update to the
preferred location to avoid issues in the future with potential deprecations.

A sample configuration file may be found in `/opt/datadog-agent/etc/datadog-agent`.

A basic configuration will typically require a destination `dd_url` and  your
datadog API key. Occassionally a proxy configuration must be specified depending
on your network setup.

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

Dogstatsd relies on the same configuration file defined for the agent and runs in
a separate process. To run `dogstatsd` you may do the following:

```bash
cd /opt/datadog-agent/agent
./dogstatsd.py
```

Note that `dogstatsd` doesn't currently daemonize and will run in the foreground.

There are also facilities to run the agent via the known python `supervisor`, this
might be your preferred way to manage the agent daemon if you are familiar with the
tool. There are currently entries for both the `agent` and `dogstatsd`.


### Integrations

Additional integrations currently available or in development:
 - process
 - lparstats
 - hmc

For non-core integrations, a configuration file should be put in place to enable
the integration. These are expected to be found in `./etc/datadog-agent/conf.d`.
The name of the YAML configuration file should match that of the integration:
`./etc/datadog-agent/conf.d/foo.yaml` will enable integration foo, and set its
configuration.

### Uninstall
To remove an installed agent you will run a similar `installp` command:
```
installp -e dd-aix-uninstall.log -uv datadog-unix-agent
```
Note how we're again logging to `dd-aix-install.log`, you may skip that by removing the `-e` switch.

#### Removing Older Agents

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

You will typically want `setuptools`, `wheel` and `virtualenv` on your python
development environment.

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
- `gem install —local ./pkg/libyajl-1.2.0.gem`

Once these steps are complete, you may go back to `omnibus/` in the agent repo and run
`bundle install` or `bundle update` once again.

If you got here you're doing good and you're almost ready to go.

##### Build Runtime Requirements + Troubleshooting

- Make sure the ulimits are high enough if you receive out of memory errors:
  - check ulimits with `ulimit -a`
  - set high enough ulimits for `stack size`, `data seg size` and `max memory size`
- Make sure you have enough space in `/opt` for the requirements + build
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

*Note*: You can override `omnibus-ruby` and `omnibus-software` gem versions if necessary with
the `OMNIBUS_RUBY_VERSION` and `OMNIBUS_SOFTWARE_VERSION` respectively - followed by a
`bundle update`.

#### Building

Triggering a build is the easiest part, we just need to specify a few more env vars currently:
- `JMXFETCH_VERSION`: JMXFetch version to bundle with the agent.
- `JMXFETCH_HASH`: SHA256 hash for the JMXFetch artifact.
- `PYTHON_VERSION`: 2 or 3 - currently only Python 2 supported.

Typically:
```
JMXFETCH_VERSION="<version>" JMXFETCH_HASH="<hash>" PYTHON_VERSION="2" bundle exec omnibus build agent --log-level=info
```

#### Deprecated: Scripted Installer

This build method has been deprecated in favor of the omnibus build. Keeping here
for historical reasons.

We provide a script in packaging named `./packaging/builder` that will allow you
to build a self-extractable installer. You may use it as follows:

```bash
./builder -b {github_branch} -v {version}
```

Where `github_branch` would be a _remote_ branch in your repository and `version`
the version for the agent release. This will result in a `ksx` self-extractable
installer that should just work across supported AIX environments.


### Integrations

The agent has two types of checks or integrations.
  - Core checks
  - Wheel checks

The core checks are part of the agent core and are good to go. Wheels checks must
be installed as wheels (if you're using the installer they will be installed automatically).

First install the `checks-base` wheel:
```bash
pip install -c requirements.txt --no-index --find-links file://path/to/repo/deps/env/ /path/to/repo/checks/bundled/datadog_checks_base
```

Then install any wheel check you wish (HMC in this example):
```bash
pip install -c requirements.txt --no-index --find-links file://path/to/repo/deps/env/ /path/to/repo/checks/bundled/hmc
```

### AIX
If you wish to develop directly on an AIX rig, we recommend the following development
requirements be met. We will assume these conditions are met when we discuss AIX
development workflows:
 - yum (use script here: https://ftp.software.ibm.com/aix/freeSoftware/aixtoolbox/ezinstall/ppc/yum.sh)
 - python2.7+ _(should be installed with the yum script)_
 - python-tools _(should be installed with the yum script)_
 - gcc _(install with yum)_
 - virtualenv _(recommended)_


Unfortunately on AIX assuming a compiler will be available is a bit far-fetched. This
repository provides pre-built AIX wheels for 6.1, 7.1 and 7.2 environments. They may
be found in the `deps/` directory.

You may install the wheels if you're developing on AIX into your environment like this:

```bash
python -m pip install --no-index --find-links file:///path/to/repo/deps/env -r requirements.txt
```

Most wheels we've pre-compiled required some manual work to build. Though the XL compiler
is perhaps the expected compiler on AIX rigs, XL is not free and we have built the
dependencies relying on GCC (available via yum). We will also assume the python version
installed is provided by the AIX Linux toolbox (rpm package) via rpm/yum (*not* the AIXTOOLS
version).

You will typically download the python package source tarball, untar, `cd <python-package>` and
compile as follows:

```bash
CC="gcc -lgcc"  LDSHARED="/opt/freeware/lib/python2.7/config/ld_so_aix gcc -bI:/opt/freeware/lib/python2.7/config/python.exp" CFLAGS="-fno-strict-aliasing -Wall  -Wstrict-prototypes -fPIC -O2" python setup.py bdist_wheel
```

The command above is a blueprint, but might require some tweaking as far as the include (`-I`) and
lib (`-L`) directives may go.

If the command succeeds you'll typically find the compiled wheel in the python-package `dist/`
directory.

#### psutil

We are currently working on merging some changes upstream into `psutil` to avoid having to apply
any patches manually, but until then please use the `psutil.patch` file provided in the `patch/`
subdir on the vanilla psutil:

Clone the `psutil` repository somewhere in your filesystem, keep the repositories separate, so
clone this outside of `datadog-unix-agent`.

```
git clone git@github.com:giampaolo/psutil.git
patch -p0 < psutil.patch
```

Happy DataDoggin'!
