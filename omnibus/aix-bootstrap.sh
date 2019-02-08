#!/bin/bash

OMNIBUS_DIR=$(dirname "$0")
GCC_VERSION=6.3.0-2
YUM_URL=http://ftp.software.ibm.com/aix/freeSoftware/aixtoolbox/ezinstall/ppc/yum.sh
CURL_URL=http://www.aixtools.net/index.php/curl
LIBYAJL_GEM_URL=https://github.com/truthbk/libyajl2-gem/tarball/jaime/aix
LIBYAJL_GEM_TARBALL=libyajl2-gem.tar.gz
LIBYAJL_GEM_DIR=$(echo $LIBYAJL_GEM_TARBALL | cut -f1 -d.)
YAJL_URL=https://github.com/lloyd/yajl/tarball/12ee82ae5138ac86252c41f3ae8f9fd9880e4284
YAJL_TARBALL=yajl.tar.gz
YAJL_DIR=$(echo $YAJL_TARBALL | cut -f1 -d.)
CURL_CMD="curl -s -L -o"
GNU_TAR="/opt/freeware/bin/tar"

function is_sudo {
    if [ $(id -u) -eq "0" ]; then
        return 0
    else
        return 1
    fi
}

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

# removing unneeded stuff...
echo "removing unnecessary dependencies..."
yum remove -y -q gcc-locale gcc libgcc gcc-c++ libstdc++

# installing compiler dependencies 
echo "installing compiler build dependencies..."
yum install -y -q gcc-$GCC_VERSION
yum install -y -q gcc-c++-$GCC_VERSION

# installing build dependencies
echo "installing additional build dependencies..."
yum install -y -q coreutils sudo libffi libffi-devel ruby ruby-devel tar curl git

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
bundle install
bundle exec rake prep
bundle exec rake compile
bundle exec rake package
gem install --local /tmp/$LIBYAJL_GEM_DIR/pkg/libyajl2-1.2.0.gem

echo "installing omnibus dependencies..." 
cd $OMNIBUS_DIR
bundle install

echo "setting git attributes (if available)..." 
if [ ! -z "$GIT_NAME"]; then
    git config --global user.name $GIT_NAME
fi

if [ ! -z "$GIT_EMAIL"]; then
    git config --global user.email $GIT_EMAIL
fi

echo "you should be ready to go..."
