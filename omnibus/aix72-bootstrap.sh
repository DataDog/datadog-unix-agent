#!/usr/bin/ksh
# Bootstrap script for AIX 7.2 TL4 omnibus build environment.
# Uses IBM AIX Toolbox packages from public.dhe.ibm.com.
# Falls back to direct rpm installs if yum.sh bootstrap fails.

set -e

IBM_DHE="https://public.dhe.ibm.com/aix/freeSoftware/aixtoolbox"
YUM_SH_URLS=(
    "https://public.dhe.ibm.com/aix/freeSoftware/aixtoolbox/ezinstall/ppc/yum.sh"
    "http://ftp.software.ibm.com/aix/freeSoftware/aixtoolbox/ezinstall/ppc/yum.sh"
)
LIBYAJL_GEM_URL="https://github.com/truthbk/libyajl2-gem/tarball/jaime/aix"
LIBYAJL_GEM_TARBALL="libyajl2-gem.tar.gz"
LIBYAJL_GEM_DIR="libyajl2-gem"
YAJL_URL="https://github.com/lloyd/yajl/tarball/12ee82ae5138ac86252c41f3ae8f9fd9880e4284"
YAJL_TARBALL="yajl.tar.gz"
YAJL_DIR="yajl"
GNU_TAR="/opt/freeware/bin/tar"

if [ $(id -u) -ne 0 ]; then
    echo "Please run this script as root (or via sudo)."
    exit 1
fi

if ! which curl > /dev/null 2>&1; then
    echo "ERROR: curl is required. Install it from IBM AIX Toolbox first:"
    echo "  rpm -Uvh $IBM_DHE/RPMS/ppc/curl/curl-8.14.1-1.aix7.1.ppc.rpm"
    exit 1
fi

# --- Space checks ---
typeset -i tmp_req=300
tmp_free=$(echo "scale=0; $(df -Pm /tmp | sed -e /Filesystem/d | awk '{print $4}') / 1" | bc)
if [ "$tmp_free" -le "$tmp_req" ]; then
    echo "ERROR: /tmp needs at least ${tmp_req}MB free. Currently: ${tmp_free}MB"
    exit 1
fi

typeset -i opt_req=2048
opt_free=$(echo "scale=0; $(df -Pm /opt | sed -e /Filesystem/d | awk '{print $4}') / 1" | bc)
if [ "$opt_free" -le "$opt_req" ]; then
    echo "ERROR: /opt needs at least ${opt_req}MB free. Currently: ${opt_free}MB"
    echo "Use: chfs -a size=+2G /opt"
    exit 1
fi

# --- Install yum ---
install_yum_via_sh() {
    for url in "${YUM_SH_URLS[@]}"; do
        echo "Trying yum bootstrap from $url ..."
        if curl -L -o /tmp/yum.sh "$url" 2>/dev/null && [ -s /tmp/yum.sh ]; then
            sh /tmp/yum.sh && return 0
        fi
    done
    return 1
}

# Package URLs for direct rpm install (fallback if yum.sh unavailable)
# Ordered by dependency: libs first, then tools
DIRECT_RPMS=(
    # GCC runtime libs (for AIX 7.2, stable)
    "$IBM_DHE/RPMS/ppc-7.2/gcc/libgcc-6.3.0-2.aix7.2.ppc.rpm"
    "$IBM_DHE/RPMS/ppc-7.2/gcc/libstdcplusplus-6.3.0-2.aix7.2.ppc.rpm"
    # GCC compiler for AIX 7.2 (stable 6.3.0; includes g++)
    "$IBM_DHE/RPMS/ppc-7.2/gcc/gcc-6.3.0-2.aix7.2.ppc.rpm"
    # GCC 8.3.0 beta for AIX 7.2 (better optimizations, comment out if unstable)
    # "$IBM_DHE/RPMS/beta/gcc/libgcc-8.3.0-3_beta.aix7.2.ppc.rpm"
    # "$IBM_DHE/RPMS/beta/gcc/libstdc++-8.3.0-3_beta.aix7.2.ppc.rpm"
    # "$IBM_DHE/RPMS/beta/gcc/gcc-8.3.0-3_beta.aix7.2.ppc.rpm"
    # "$IBM_DHE/RPMS/beta/gcc/gcc-c++-8.3.0-3_beta.aix7.2.ppc.rpm"
    # Math libs (GCC build deps, also needed by some omnibus software)
    "$IBM_DHE/RPMS/ppc/mpfr/mpfr-4.2.1-1.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/gmp/gmp-6.3.0-1.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/libmpc/libmpc-1.3.1-1.aix7.1.ppc.rpm"
    # libffi (required by Ruby and Python ctypes)
    "$IBM_DHE/RPMS/ppc-7.2/gcc/libffi-3.0.12-1.aix7.2.ppc.rpm"
    "$IBM_DHE/RPMS/ppc-7.2/gcc/libffi-devel-3.0.12-1.aix7.2.ppc.rpm"
    # readline (required by Ruby)
    "$IBM_DHE/RPMS/ppc-6.1/readline/readline-8.1-1.aix6.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc-6.1/readline/readline-devel-8.1-1.aix6.1.ppc.rpm"
    # zlib (needed by curl, git, Python)
    "$IBM_DHE/RPMS/ppc/zlib/zlib-1.2.13-1.aix7.1.ppc.rpm"
    # gettext (needed by git and other tools)
    "$IBM_DHE/RPMS/ppc/gettext/gettext-0.21-2.aix7.1.ppc.rpm"
    # Ruby 2.7.5 (for omnibus)
    "$IBM_DHE/RPMS/ppc-6.1/ruby/ruby-2.7.5-1.aix6.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc-6.1/ruby/ruby-devel-2.7.5-1.aix6.1.ppc.rpm"
    # Build tools
    "$IBM_DHE/RPMS/ppc/coreutils/coreutils-9.5-1.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/tar/tar-1.35-2.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/make/make-4.4.1-1.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/patch/patch-2.7.6-2.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/curl/curl-8.14.1-1.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/git/git-2.51.2-1.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/sudo/sudo-1.9.13p2-1.aix7.1.ppc.rpm"
    "$IBM_DHE/RPMS/ppc/binutils/binutils-2.44-1.aix7.1.ppc.rpm"
)

install_packages_direct() {
    echo "Installing packages directly from IBM DHE via rpm..."
    mkdir -p /tmp/aix_rpms
    for url in "${DIRECT_RPMS[@]}"; do
        pkg=$(basename "$url")
        echo "Downloading $pkg ..."
        curl -L -o "/tmp/aix_rpms/$pkg" "$url" || { echo "WARN: failed to download $pkg, skipping"; continue; }
        echo "Installing $pkg ..."
        rpm -Uvh --nodeps "/tmp/aix_rpms/$pkg" 2>/dev/null || rpm -Fvh --nodeps "/tmp/aix_rpms/$pkg" 2>/dev/null || echo "WARN: $pkg already installed or failed, continuing"
    done
}

# --- Main package installation ---
if which yum > /dev/null 2>&1; then
    echo "yum already available, using it to install/update packages..."
    PATH="/opt/freeware/sbin:/opt/freeware/bin:/opt/bin:$PATH"
    yum install -y -q mpfr gmp libmpc libgcc libstdc++ gcc
    yum install -y -q coreutils sudo libffi libffi-devel readline readline-devel \
        ruby ruby-devel tar curl git patch make zlib gettext binutils
else
    echo "yum not found. Attempting yum.sh bootstrap..."
    if install_yum_via_sh; then
        echo "yum.sh bootstrap succeeded."
        PATH="/opt/freeware/sbin:/opt/freeware/bin:/opt/bin:$PATH"
        yum install -y -q mpfr gmp libmpc libgcc libstdc++ gcc
        yum install -y -q coreutils sudo libffi libffi-devel readline readline-devel \
            ruby ruby-devel tar curl git patch make zlib gettext binutils
    else
        echo "yum.sh bootstrap failed. Falling back to direct rpm installs..."
        install_packages_direct
    fi
fi

export PATH="/opt/freeware/sbin:/opt/freeware/bin:/opt/bin:$PATH"

# Verify key tools
for cmd in gcc ruby curl git; do
    if ! which "$cmd" > /dev/null 2>&1; then
        echo "ERROR: $cmd not found after installation. Manual intervention required."
        exit 1
    fi
done
echo "GCC: $(gcc --version | head -1)"
echo "Ruby: $(ruby --version)"

# --- Update CA certificates ---
echo "Updating CA certificates..."
curl -L https://curl.se/ca/cacert.pem -o /opt/freeware/etc/ssl/certs/extracted/pem/tls-ca-bundle.pem 2>/dev/null || true

# Remove expired DST Root CA X3 (LetsEncrypt compatibility fix)
if [ -f /opt/freeware/etc/ssl/certs/DST_Root_CA_X3.crt ]; then
    rm /opt/freeware/etc/ssl/certs/DST_Root_CA_X3.crt
fi

# --- Ruby patching for DNS (SiteOx workaround) ---
echo "Patching Ruby http.rb for DNS resolution..."
HTTPRB=$(rpm -ql ruby 2>/dev/null | grep "net/http.rb" | head -1)
if [ -n "$HTTPRB" ] && ! grep -q "resolv-replace" "$HTTPRB"; then
    cp "$HTTPRB" "${HTTPRB}.orig"
    echo "require 'resolv-replace'" >> "$HTTPRB"
fi

# --- ulimits ---
echo "Setting ulimits..."
ulimit -d unlimited
ulimit -s unlimited
ulimit -m unlimited

# --- Install bundler ---
echo "Installing bundler gem..."
gem install bundler --no-ri --no-rdoc 2>/dev/null || gem install bundler

# --- Install libyajl2 gem (omnibus dependency, AIX-patched fork) ---
echo "Building libyajl2 gem (omnibus dependency)..."
mkdir -p /tmp/libyajl2_build
cd /tmp/libyajl2_build

curl -L -o "$LIBYAJL_GEM_TARBALL" "$LIBYAJL_GEM_URL"
mkdir -p "$LIBYAJL_GEM_DIR"
"$GNU_TAR" xzf "$LIBYAJL_GEM_TARBALL" -C "./$LIBYAJL_GEM_DIR" --strip=1

cd "/tmp/libyajl2_build/$LIBYAJL_GEM_DIR/ext/libyajl2/vendor/"
curl -L -o "$YAJL_TARBALL" "$YAJL_URL"
mkdir -p "./$YAJL_DIR"
"$GNU_TAR" xzf "$YAJL_TARBALL" -C "./$YAJL_DIR" --strip=1

cd "/tmp/libyajl2_build/$LIBYAJL_GEM_DIR"
bundle install --without development_extras
bundle exec rake prep
bundle exec rake compile
bundle exec rake package
gem install --local /tmp/libyajl2_build/"$LIBYAJL_GEM_DIR"/pkg/libyajl2-1.2.0.gem

# --- Git config ---
if [ -z "$(git config user.name 2>/dev/null)" ]; then
    git config --global user.name "Datadog"
fi
if [ -z "$(git config user.email 2>/dev/null)" ]; then
    git config --global user.email "package@datadoghq.com"
fi

echo ""
echo "Bootstrap complete. The AIX 7.2 build environment is ready."
echo "Next steps:"
echo "  git clone --branch 1.2.0 https://github.com/DataDog/datadog-unix-agent.git /root/datadog-unix-agent"
echo "  cd /root/datadog-unix-agent/omnibus"
echo "  bundle install --binstubs"
echo "  ulimit -d unlimited; ulimit -s unlimited; ulimit -m unlimited"
echo "  bundle exec omnibus build agent --log-level=info"
