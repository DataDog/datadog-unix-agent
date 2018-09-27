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

### Development Requirements
 - yum (use script here: https://ftp.software.ibm.com/aix/freeSoftware/aixtoolbox/ezinstall/ppc/yum.sh)
 - python2.7+ _(should be installed with the yum script)_
 - python-tools _(should be installed with the yum script)_ 
 - gcc _(install with yum)_
 - virtualenv _(recommended)_

#### Running the agent
To keep everything nice and clean we will stick to a virtual environment.

```bash
pip install virtualenv
```

Now let's create a virtual environment (assuming you're in the repo root and running bash):

```bash
mkdir venv
. ./venv/bin/activate
```

##### Runtime requirements
Most requirements can be transparently installed using the bundled requirements
file.
```bash
pip install -r requirements.txt
```

If you're on Linux, or FreeBSD (and many others), you're probably good to go. However on AIX you
would need the XL compiler available on the machine to be able to build. XL is not free and so we
will not assume it will be available on your LPAR. Fortunately there are ways around this. 

Currently the following steps should be executed **before** attempting to install via the 
requirements file provided in the repository.

We are currently working on merging some changes upstream into `psutil` to avoid having to apply 
any patches manually, but until then please use the `psutil.patch` file provided in the `patch/`
subdir on the vanilla psutil:

Clone the `psutil` repository somewhere in your filesystem, keep the repositories separate, so
clone this outside of `datadog-unix-agent`.

```
git clone git@github.com:giampaolo/psutil.git
patch -p0 < psutil.patch
```

Then build the python package:

```
CC="gcc -lgcc"  LDSHARED="/opt/freeware/lib/python2.7/config/ld_so_aix gcc -bI:/opt/freeware/lib/python2.7/config/python.exp" CFLAGS="-fno-strict-aliasing -Wall  -Wstrict-prototypes -fPIC -O2" python setup.py bdist_wheel 
pip install dist/psutil-5.4.5-cp27-cp27-aix_6_1.whl  # or similar 
```

Now head back to the `datadog-unix-agent` repo and install the remaining dependencies:

```bash
pip install -r requirements.txt
```

At this point you should be ready to go!

### Running the agent

To run the agent you may simply execute:

```bash
DD_LOG_LEVEL=debug DD_API_KEY=<api_key_here> ./agent.py start
```

You may also drop a configuration file `datadog.yaml` in the repo root (you may use the example 
file provided in the repo). Other more UNIX appropriate locations are supported (namely
`/etc/datadog-agent` but packaging isn't currently available). When using a config file instead
of environment variables to specify configuration params, launch like this:

```bash
./agent.py start
```

Config file will be searched in this order:
- `./datadog.yaml`
- `/etc/datadog-agent/datadog.yaml`


By default, the agent will run in the foreground.

There are also facilities to run the agent both daemonized and via a `supervisor`, this would
probably be the preferred way to manage your daemons (`agent` and `dogstatsd`).


Happy DataDoggin'!

