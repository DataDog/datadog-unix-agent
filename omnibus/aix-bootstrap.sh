#!/bin/bash

VERBOSE=${VERBOSE:-0}
PROJECT_TARGET_DIR=$(pwd)
USE_GIT=${USE_GIT:-1}
PROJECT_BRANCH=${PROJECT_BRANCH:-master}
PROJECT_URL="https://github.com/DataDog/datadog-unix-agent/tarball/${PROJECT_BRANCH}"
PROJECT_GIT_REPO="https://github.com/DataDog/datadog-unix-agent.git"
PROJECT_TARBALL="datadog-unix-agent.tar.gz"
PROJECT_DIR=$(echo $PROJECT_TARBALL | cut -f1 -d.)
YUM_URL="http://ftp.software.ibm.com/aix/freeSoftware/aixtoolbox/ezinstall/ppc/yum.sh"
CURL_URL="http://www.aixtools.net/index.php/curl"
LIBYAJL_GEM_URL="https://github.com/truthbk/libyajl2-gem/tarball/jaime/aix"
LIBYAJL_GEM_TARBALL="libyajl2-gem.tar.gz"
LIBYAJL_GEM_DIR=$(echo $LIBYAJL_GEM_TARBALL | cut -f1 -d.)
YAJL_URL="https://github.com/lloyd/yajl/tarball/12ee82ae5138ac86252c41f3ae8f9fd9880e4284"
YAJL_TARBALL="yajl.tar.gz"
YAJL_DIR=$(echo $YAJL_TARBALL | cut -f1 -d.)
CURL_CMD="curl -s -L -o"
GNU_TAR="/opt/freeware/bin/tar"

# version pins
GCC_VERSION=${GCC_VERSION:-6.3.0-2} # unsued
COREUTILS_VERSION=${COREUTILS_VERSION:-8.29-3}
CURL_VERSION=${CURL_VERSION:-7.64.0-1}
LIBFFI_VERSION=${LIBFFI_VERSION:-3.2.1-3}
MPFR_VERSION=${MPFR_VERSION:-3.1.2-3} # unsued
RUBY_VERSION=${RUBY_VERSION:-2.5.1-1}
SUDO_VERSION=${SUDO_VERSION:-1.8.21p2-1}
TAR_VERSION=${TAR_VERSION:-1.30-1}
GIT_VERSION=${GIT_VERSION:-2.18.0-1}

function is_sudo {
    if [ $(id -u) -eq "0" ]; then
        return 0
    else
        return 1
    fi
}

if [ "$VERBOSE" -ne "0" ]; then
    set -x
fi

if ! is_sudo; then
    echo "Please run this script with super-user powers."
    echo "Bailing out!"
    exit 1
fi

#Check if /tmp has enough space to download rpm.rte & yum_bundle and size for
#Extracting rpm packages.
# 45 MB for rpm.rte and 54 MB for yum_bundle.tar, 50 MB for rpm packages extracted.
typeset -i total_req=$(echo "(45+54+50)" | bc)
tmp_free=$(echo "scale=0; $(df -Pm /tmp | sed -e /Filesystem/d | awk '{print $4}') / 1" | bc)
if [[ $tmp_free -le $total_req ]]
then
   echo "Please make sure /tmp has 149MB of free space to download rpm.rte & yum_bundle.tar files,"
   echo "and space required for extracting the rpm packages."
   exit 1
fi

# curl is needed to download stuff
if ! which curl; then
    echo "curl not available, you will need to install it manually."
    echo "you may find an AIX native package here: $CURL_URL."
    exit 1
fi

# yum is needed to pull in deps
if ! which yum; then
    echo "downloading AIX linux toolbox..."
    $CURL_CMD /tmp/yum.sh $YUM_URL
    echo "installing AIX linux toolbox..."
    sh /tmp/yum.sh
fi

PATH="/opt/freeware/sbin:/opt/freeware/bin:/opt/bin:$PATH"

# exit on errors
set -e

# assuming 2GB of space necessary on /opt
total_req=2048
opt_free=$(echo "scale=0; $(df -Pm /opt | sed -e /Filesystem/d | awk '{print $4}') / 1" | bc)
if [[ $opt_free -le $total_req ]]
then
   echo "Please make sure /opt has 1024 MB of free space for all deps,"
   echo "Add space with \`chfs -a size=+2G /opt\`."
   exit 1
fi

echo "installing compiler build dependencies..."
yum install -y -q mpfr mpfr-devel
yum install -y -q libgcc libstdc++ gcc gcc-c++

# installing build dependencies
echo "installing additional build dependencies..."
yum install -y -q coreutils-${COREUTILS_VERSION} sudo-${SUDO_VERSION} libffi-${LIBFFI_VERSION} libffi-devel-${LIBFFI_VERSION} \
    ruby-${RUBY_VERSION} ruby-devel-${RUBY_VERSION} tar-${TAR_VERSION} curl-${CURL_VERSION} git-${GIT_VERSION}

echo "installing additional bootstrap dependencies..."
echo "setting better ulimits..."
ulimit -d 524288
ulimit -s 524288
ulimit -m 524288

# installing ruby deps
echo "installing ruby dependencies..."
gem install bundler
$CURL_CMD /tmp/$LIBYAJL_GEM_TARBALL $LIBYAJL_GEM_URL
cd /tmp
mkdir -p $LIBYAJL_GEM_DIR
$GNU_TAR xvzf $LIBYAJL_GEM_TARBALL -C ./$LIBYAJL_GEM_DIR --strip=1

cd /tmp/$LIBYAJL_GEM_DIR/ext/libyajl2/vendor/
$CURL_CMD ./$YAJL_TARBALL $YAJL_URL
mkdir -p ./$YAJL_DIR
$GNU_TAR xvzf $YAJL_TARBALL -C ./$YAJL_DIR --strip=1

cd /tmp/$LIBYAJL_GEM_DIR
bundle install --without development_extras
bundle exec rake prep
bundle exec rake compile
bundle exec rake package
gem install --local /tmp/$LIBYAJL_GEM_DIR/pkg/libyajl2-1.2.0.gem

echo "setting git attributes (if available)..."
if [ ! -z "$GIT_NAME" ]; then
    git config --global user.name "$GIT_NAME"
fi

if [ ! -z "$GIT_EMAIL" ]; then
    git config --global user.email "$GIT_EMAIL"
fi

echo "pulling AIX agent project..."
cd $PROJECT_TARGET_DIR
if [ "$USE_GIT" -eq "0" ]; then
  mkdir -p $PROJECT_DIR
  $CURL_CMD ./$PROJECT_TARBALL $PROJECT_URL
  $GNU_TAR xvzf $PROJECT_TARBALL -C ./$PROJECT_DIR --strip=1
else
  git clone -b $PROJECT_BRANCH $PROJECT_GIT_REPO $PROJECT_DIR
fi

echo "installing omnibus dependencies..."
cd ./${PROJECT_DIR}/omnibus
bundle install

echo "you should be ready to go..."
