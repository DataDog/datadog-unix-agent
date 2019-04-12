#!/bin/ksh
# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# Datadog Agent installation script: install and set up the Agent on supported Linux distributions
# using the package manager and Datadog repositories.

set -e
logfile="ddagent-install.log"

CHANNEL=${CHANNEL:-stable}
VERSION=${VERSION:-latest}
AIX_ARTIFACT_SOURCE=${AIX_ARTIFACT_SOURCE:-https://s3.amazonaws.com/dd-unix-agent}
SHUTDOWN_WAIT=${SHUTDOWN_WAIT:-8}  # 8 + 7 + ... + 2 + 1 secs
TMP_LOC=${TMP_LOC:/tmp}  # 8 + 7 + ... + 2 + 1 secs

ETCDIR="/etc/datadog-agent"
CONF="$ETCDIR/datadog.yaml"

if [ $(command -v curl) ]; then
    dl_cmd="curl -f -L"
    insecure_flag="-k"
elif [ $(command -v wget) ]; then
    dl_cmd="wget --quiet"
    insecure_flag="--no-check-certificate"
else
    printf "\033[31mcurl or wget are required to use this script.\033[0m\n"
    exit 1;
fi

# Set up a named pipe for logging
npipe=${TMP_LOC}/$$.tmp
mknod $npipe p

# Log all output to a log for error checking
tee <$npipe $logfile &
exec 1>&-
exec 1>$npipe 2>&1
trap "rm -f $npipe" EXIT


on_error() {
    printf "\033[31m$ERROR_MESSAGE
It looks like you hit an issue when trying to install the Agent.

Troubleshooting and basic usage information for the Agent are available at:

    https://docs.datadoghq.com/agent/basic_agent_usage/

If you're still having problems, please send an email to support@datadoghq.com
with the contents of ddagent-install.log and we'll do our very best to help you
solve your problem.\n\033[0m\n"
}
trap on_error ERR

use_proxy_creds=
if [ -n "$PROXY_USER" -a -n "$PROXY_PASSWORD" ]; then
  use_proxy_creds=true
elif [ -n "$PROXY_USER" -o -n "$PROXY_PASSWORD" ]; then
    printf "\033[31When using proxy credentials you must specify both PROXY_USER and PROXY_PASSWORD\033[0m\n"
    exit 1;
fi

if [ -n "$DD_HOSTNAME" ]; then
    dd_hostname=$DD_HOSTNAME
fi

if [ -n "$DD_SITE" ]; then
    site="$DD_SITE"
fi

if [ -n "$DD_API_KEY" ]; then
    apikey=$DD_API_KEY
fi

no_start=
if [ -n "$DD_INSTALL_ONLY" ]; then
    no_start=true
fi

# comma-separated list of tags
if [ -n "$DD_HOST_TAGS" ]; then
    host_tags=$DD_HOST_TAGS
fi

dd_upgrade=
if [ -n "$DD_UPGRADE" ]; then
  dd_upgrade=$DD_UPGRADE
fi

if [ -n "$INSECURE" ]; then
    dl_cmd="${dl_cmd} ${insecure_flag}"
fi

if [ -n "$PROXY" ]; then

  if [ $(command -v curl) ]; then
    # curl
    dl_cmd="${dl_cmd} -x $PROXY"
    if [ ! -z "${use_proxy_creds}" ]; then
      dl_cmd="${dl_cmd} -U $PROXY_USER:$PROXY_PASSWORD"
    fi
  else
    # wget
    dl_cmd="${dl_cmd} -e use_proxy=on -e http_proxy=$PROXY -e https_proxy=$PROXY"
    if [ ! -z "${use_proxy_creds}" ]; then
      dl_cmd="${dl_cmd} --proxy_user=$PROXY_USER --proxy_password=$PROXY_PASSWORD"
    fi
  fi
fi

if [ ! "${apikey}" ]; then
  # if it's an upgrade, then we need an existing config
  if [ ! -z "${dd_upgrade}" -a ! -e "${CONF}" ]; then
    printf "\033[31mAPI key not available in DD_API_KEY environment variable.\033[0m\n"
    exit 1;
  fi
fi

# Root user detection
if [ $(echo "$(id -ru)") = "0" ]; then
    sudo_cmd=''
else
    sudo_cmd='sudo'
fi

# OS/Distro Detection
OS=$(uname -s)
OS_LOWER=$(echo $OS | tr "[:upper:]" "[:lower:]")

# Install the necessary package sources
if [ "$OS" = "AIX" ]; then
    ARCH=$(uname -p)
    MAJOR=$(uname -v)
    MINOR=$(uname -r)
    INSTALL_UPGRADE_FLAGS="-aXYgd"
    REINSTALL_FLAGS="-acFNXYd"

    printf "\033[34m\n* Downloading version ${VERSION} if available...\n\033[0m\n"
    BFF="datadog-unix-agent-${VERSION}.${ARCH}.aix.${MAJOR}.${MINOR}.bff"
    $dl_cmd -o ${TMP_LOC}/${BFF} ${AIX_ARTIFACT_SOURCE}/${OS_LOWER}/${CHANNEL}/${BFF}

    INSTALLED_FILESET=$(lslpp -l "datadog-unix-agent" 2>&1 | grep -i datadog-unix-agent | awk '{ print $2 }' | head -n 1)
    CURRENT_FILESET=$(installp -ld ${TMP_LOC}/${BFF} 2>&1 | grep -i datadog-unix-agent | awk '{ print $2 }' | head -n 1)
    INSTALL_FLAGS=$INSTALL_UPGRADE_FLAGS
    if [ "$INSTALLED_FILESET" = "$CURRENT_FILESET" ]; then
        INSTALL_FLAGS=$REINSTALL_FLAGS
    fi

    printf "\033[34m\n* Installing the Datadog Agent package\n\033[0m\n"
    ERROR_MESSAGE="ERROR
Failed to install the Datadog package.
See the logs above to determine the cause.
If the cause is unclear, please contact Datadog support.
*****
"
    installp ${INSTALL_FLAGS} ${TMP_LOC}/${BFF} datadog-unix-agent
    ERROR_MESSAGE=""
else
    printf "\033[31mYour OS or distribution are not supported by this install script.
Please follow the instructions on the Agent setup page:

    https://app.datadoghq.com/account/settings#agent\033[0m\n"
    exit;
fi

# Set the configuration
tmp_config=${TMP_LOC}/dd-tmp-config.$$
trap "rm -f $tmp_config" EXIT
if [ -e "${CONF}" -a -z "${dd_upgrade}" ]; then
  printf "\033[34m\n* Keeping old datadog.yaml configuration file\n\033[0m\n"
else
  if [ ! -e "${CONF}" ]; then
    $sudo_cmd cp $CONF.example $CONF
  fi
  if [ "${apikey}" ]; then
    printf "\033[34m\n* Adding your API key to the Agent configuration: $CONF\n\033[0m\n"
    $sudo_cmd sh -c "sed 's/api_key:.*/api_key: $apikey/' $CONF" > $tmp_config
    $sudo_cmd mv $tmp_config $CONF
  else
    # if for whatever reason there's no key, don't start
    if ! $sudo_cmd grep -q -E '^api_key: .+' $CONF; then
      printf "\033[31mThe Agent won't start automatically at the end of the script because the Api key is missing, please add one in datadog.yaml and start the agent manually.\n\033[0m\n"
      no_start=true
    fi
  fi
  if [ $site ]; then
    printf "\033[34m\n* Setting SITE in the Agent configuration: $CONF\n\033[0m\n"
    $sudo_cmd sh -c "sed 's|# site:.*|site: $site|' $CONF" > $tmp_config
    $sudo_cmd mv $tmp_config $CONF
  fi
  if [ -n "$DD_URL" ]; then
    $sudo_cmd sh -c "sed 's|# dd_url:.*|dd_url: $DD_URL|' $CONF" > $tmp_config
    $sudo_cmd mv $tmp_config $CONF
  fi
  if [ $dd_hostname ]; then
    printf "\033[34m\n* Adding your HOSTNAME to the Agent configuration: $CONF\n\033[0m\n"
    $sudo_cmd sh -c "sed 's|# hostname:.*|hostname: $dd_hostname|' $CONF" > $tmp_config
    $sudo_cmd mv $tmp_config $CONF
  fi
  if [ $host_tags ]; then
      printf "\033[34m\n* Adding your HOST TAGS to the Agent configuration: $CONF\n\033[0m\n"
      formatted_host_tags="['"$( echo "$host_tags" | sed "s|,|','|g" )"']"  # format `env:prod,foo:bar` to yaml-compliant `['env:prod','foo:bar']`
      $sudo_cmd sh -c "sed \"s|# tags:.*|tags: "$formatted_host_tags"/\" $CONF" > $tmp_config
      $sudo_cmd mv $tmp_config $CONF
  fi
  $sudo_cmd chown dd-agent:dd-agent $CONF
  $sudo_cmd chmod 640 $CONF
fi


# AIX.
# TODO: make into an if block

if [ $OS = "AIX" ]; then
  stop_instructions="$sudo_cmd stopsrc -s datadog-agent"
  wait_instructions="CNT=0; echo \"Waiting for the agent to stop\"; until lssrc -s datadog-agent | grep -q inoperative || [ \$CNT -eq $SHUTDOWN_WAIT ]; do sleep \$(( CNT=CNT+1 )); done"
  start_instructions="$sudo_cmd startsrc -s datadog-agent"
fi


if [ ! -z "${no_start}" ]; then
    printf "\033[34m
* DD_INSTALL_ONLY environment variable set or no complete config available:
the newly installed version of the agent will not be started. You will have
to do it manually using the following commands:

    $stop_instructions || $wait_instructions && $start_instructions

* should the wait expire, please run $start_instructions manually once the
service has stopped.

\033[0m\n"
    exit 0
fi

printf "\033[34m* Starting the Agent...\n\033[0m\n"
$stop_instructions || true
eval "${wait_instructions}" && $start_instructions

# Metrics are submitted, echo some instructions and exit
printf "\033[32m

Your Agent is running and functioning properly. It will continue to run in the
background and submit metrics to Datadog.

If you ever want to stop the Agent, run:

    $stop_instructions

And to run it again run:

    $start_instructions

\033[0m"
