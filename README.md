# Datadog Unix Agent

A full fledged Agent specifically designed for Unix-based systems. 

Note: This agent is currently in development for AIX. It has not been tested on other systems. If
you're interested in using it, please contact our [support team](https://docs.datadoghq.com/help/).

This agent targets miscellaneous Unix operating systems not supported by our currently available
agents. To do so, it has been stripped of unnecessary bloat and cut around irrelevant use-cases 
given the target platforms, sometimes at the expense of certain features. To maximize portability
the agent will attempt to reduce the number of non pure-python dependencies to a minimum, and rely
on packages with native support for the targeted OSes (AIX currently).

## AIX

The installer is currently a rudimentary scripted self-extracting korn shell script. The tarball
included with the installer should include all requirements other than the baseline requirements.
The baseline requirements have been deemed too critical to be automated and require an attended
install. The installer is self-contained and does not require internet access.

The installer may be executed as follows (as root):

```bash
./datadog-aix-installer.{version}.ksx
```

This will install the agent in `/opt/datadog/datadog-unix-agent`. 

Please bear in mind that on upgrades, though configuration will be preserved, all other contents
in the agent target directory will be wiped.


### Baseline Requirements
 - openssl >=1.0.1 (if you need to upgrade use the IBM fileset [here](http://www-01.ibm.com/support/docview.wss?uid=isg1fileset-1190419011)) 
 - RPM (if you need to install RPM, please use the IBM fileset [here](http://www-01.ibm.com/support/docview.wss?uid=isg1fileset1404816868))

### Runtime requirements
We have provided an installer that should be able to provide all additional requirements, including
python if it is not available. These requirements include:

#### FileSets
 - cffi

#### RPMs
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

#### Python Packages
 - asn1crypto==0.24.0
 - atomicwrites==1.1.5
 - attrs==18.1.0
 - backports-abc==0.5
 - certifi==2018.4.16
 - cffi==1.11.5 (binary wheel)
 - chardet==3.0.4
 - configparser==3.5.0
 - cryptography==2.3.1 (binary wheel)
 - enum34==1.1.6
 - funcsigs==1.0.2
 - futures==3.2.0
 - idna==2.7
 - ipaddress==1.0.22
 - mccabe==0.6.1
 - meld3==1.0.2
 - more-itertools==4.2.0
 - paramiko==2.1.5 (binary wheel)
 - pbr==4.0.4
 - pluggy==0.6.0
 - psutil==5.4.6 (binary wheel)
 - py==1.5.3
 - pyasn1==0.4.4
 - pycodestyle==2.3.1
 - pycparser==2.18
 - pyflakes==1.6.0
 - PyNaCl==1.2.1 (binary wheel)
 - PyYAML==3.12
 - requests==2.19.1
 - requests-mock==1.5.0
 - singledispatch==3.4.0.3
 - six==1.11.0
 - supervisor==3.3.4
 - tornado==5.0.2
 - uptime==3.0.1
 - urllib3==1.23

Requirements should be seamlessly installed by means of the installation script.

### Running the agent

The configuration file is recommended to be placed here:
```
/opt/datadog/datadog-unix-agent/etc/datadog-agent/datadog.yaml
```

That said, config file will be searched in this order (with the first match being
taken):
- `/etc/datadog-agent/datadog.yaml`
- `./etc/datadog-agent/datadog.yaml`
- `./datadog.yaml`

A sample configuration file may be found in `/opt/datadog/datadog-unix-agent`.

A basic configuration will typically require a destination `dd_url` and  your 
datadog API key. Occassionally a proxy configuration must be specified depending
on your network setup.

With the configuration in place just start the agent as follows:

```bash
cd /opt/datadog/datadog-unix-agent
. ./venv/bin/activate
./agent.py -b start
```

If you want to run the agent in the foreground, please omit the `-b` switch.

If you wish to override any configuration setting defined in the config file, you 
may resort to environment variables as follows:
```bash
DD_LOG_LEVEL=debug ./agent.py start
```

### Running dogstatsd

Dogstatsd allows collecting and submitting custom metrics to datadog. It listens on
a UDP port and statsd metrics may be submitted to it. These will then be relayed
to Datadog.

Dogstatsd relies on the same configuration file defined for the agent and runs in 
a separate process. To run `dogstatsd` you may do the following:

```bash
cd /opt/datadog/datadog-unix-agent
. ./venv/bin/activate
./dogstatsd.py 
```

Note that `dogstatsd` doesn't currently daemonize and will run in the foreground.

There are also facilities to run the agent via the known python `supervisor`, this 
might be your preferred way to manage the agent daemon if you are familiar with the 
tool. There are currently entries for both the `agent` and `dogstatsd`.


### Integrations

Additional integrations currently available or in development:
 - process
 - hmc

For non-core integrations, a configuration file should be put in place to enable
the integration. These are expected to be found in `./etc/datadog-agent/conf.d`.
The name of the YAML configuration file should match that of the integration:
`./etc/datadog-agent/conf.d/foo.yaml` will enable integration foo, and set its
configuration.


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

