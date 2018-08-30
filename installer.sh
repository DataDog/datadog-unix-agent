#!/bin/bash

START_PATH=$(pwd)

PSUTIL_WHEEL=

usage() {
    echo "$0 [ -a <archive> | -b <branch> ] [ -d <destination> ] [ -l ]"
    echo "  -a <archive> : specify local archive to install"
    echo "  -b <branch> : specify remote git branch to pull and install"
    echo "  -d <directory> : specify remote directory"
    echo "  -l : use local wheels provided in archive"
}

DEST=
LOCAL=
ARCHIVE=
BRANCH=

while getopts ":a:b:d:lh" opt; do
    case $opt in
        a)
            if [ ! -f $OPTARG ]; then
                echo "path to archive does not exist."
                usage
                exit 1
            fi
            ARCHIVE="$(cd $(dirname $OPTARG); pwd)/$(basename $OPTARG)"
            echo "Using local archive: $ARCHIVE" >&2

            ;;
        b)
            echo "Pulling archive for branch: $OPTARG" >&2
            BRANCH=$OPTARG
            ;;
        d)
            echo "Destination directory: $OPTARG" >&2
            DEST=$OPTARG
            ;;
        l)
            echo "Install with local wheels (provided by archive)" >&2
            LOCAL=1
            ;;
        h)
            usage
            exit 0
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            usage
            exit 1
            ;;
    esac
done


if [ ! -z $LOCAL ]; then
    AIX_VERSION=$(uname -v)
    AIX_RELEASE=$(uname -r)
    echo "This is an AIX $AIX_VERSION box - settings assets"

    case "$AIX_VERSION" in
        6|7) 
            PSUTIL_WHEEL="psutil-5.4.6-cp27-cp27-aix_${AIX_VERSION}_${AIX_RELEASE}.whl"
            ;;
        *) 
            echo "unsupported AIX version: $AIX_VERSION - bailing out"
            exit 1
            ;;
    esac
fi

which python2.7 > /dev/null
if [ $? -ne 0 ]; then
    echo "No python2.7 detected. Please install or fix PATH..."
    usage
    exit 1
fi

python -m virtualenv --version > /dev/null
if [ $? -ne 0 ]; then
    echo "No virtualenv detected. Please install or fix PATH."
    usage
    exit 1
fi

set -e

if [ -z $DEST ]; then
    echo "Please specify a destination directory..."
    usage
    exit 1
fi

if [ -d $DEST ]; then
    echo "Destination path exists its contents will be wiped"
    read -p "Are you sure? " -n 1 -r
    echo 
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        rm -rf $DEST/datadog-unix-agent
    fi
elif [ -f $DEST ]; then
    echo "Destination is a file, please specify a directory"
    usage
    exit 1
fi

echo "Working off /tmp..."
cd /tmp

if [ ! -z $ARCHIVE ]; then
    cp $ARCHIVE ./datadog-unix-agent.tar.gz
elif [ ! -z $BRANCH ]; then
    echo "Downloading tarball for branch $BRANCH"
    curl -L -o datadog-unix-agent.tar.gz https://api.github.com/repos/DataDog/datadog-unix-agent/tarball/$BRANCH
else
    echo "No local archive or remote branch was specified, exiting..."
    usage
    exit 1
fi

# if there are dirs we cant read, the find will have $? > 0
set +e
echo "Removing old downloads if any..."
find . -type d -name 'DataDog-datadog-unix-agent*' -exec rm -rf {} \; 2>/dev/null 
set -e

echo "Unpacking tarball to destination $DEST..."
gunzip datadog-unix-agent.tar.gz
tar xvf datadog-unix-agent.tar
mkdir -p $DEST
find . -type d -name 'DataDog-datadog-unix-agent*' 2>/dev/null | head -n 1 | xargs -t -I {} cp -R {} $DEST/datadog-unix-agent

echo "Setting up virtual env..."
cd $DEST/datadog-unix-agent
python -m virtualenv --python python2.7 venv
source ./venv/bin/activate

echo "Installing requirements..."
if [ -z $LOCAL ]; then
    echo "Note: you will need a compiler to setup psutil, if this fails try the local build."
    pip install -r requirements.txt
else
    pip install ./deps/psutil/$PSUTIL_WHEEL
    pip install -r requirements.txt --no-index --find-links file://$(cd $DEST; pwd)/datadog-unix-agent/deps/env/
fi
deactivate

echo "Cleaning up..."
rm /tmp/datadog-unix-agent.tar

echo "You should be good to go!"
cd $START_PATH 

set +e
