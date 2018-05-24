#!/bin/sh

set -e

if [ "$#" -ne 1 ] || ! [ -d "$1" ]; then
  echo "Usage: $0 AGENT_DIRECTORY" >&2
  exit 1
fi

if ! [ -z "$VIRTUAL_ENV" ]; then
    echo "found previous virtual environment, it will be deativated..."
fi

# get absolute path
AGENT_DIR=$(cd $1; pwd)

if [ -e "$AGENT_DIR/venv/bin/activate" ]; then
    echo "ensuring venv is pointing to the right location..."
    sed "s~VIRTUAL_ENV=.*~VIRTUAL_ENV=\"$AGENT_DIR/venv\"~g" $AGENT_DIR/venv/bin/activate > $AGENT_DIR/venv/bin/.activate_new
    mv $AGENT_DIR/venv/bin/.activate_new $AGENT_DIR/venv/bin/activate
else
    echo "no activation script found... cannot continue."
    exit 1
fi

set +e
echo "enabling virtual environment"
. $AGENT_DIR/venv/bin/activate

set -e

echo "starting agent... (press ctrl-c to stop)"
$AGENT_DIR/agent.py start

# it would be disabled anyway outside the script, but lets be explicit
echo "deactivating virtual environment"
deactivate


