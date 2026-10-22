#!/bin/sh
# Runs aix.sh against fake Unix Agent installs built from the CA bundles each
# release actually ships, with the AIX SRC commands replaced by shims.
#
# Usage: sh tests/test_aix.sh <python> [shell]
#   python  interpreter used as the fake embedded/bin/python
#   shell   shell aix.sh is run with (default: sh)
# Needs network access to curl.se and PyPI to fetch the bundles.

# shellcheck disable=SC2329 # helpers called through check()
set -u

PY=${1:?usage: $0 <python> [shell]}
SH=${2:-sh}
HERE=$(cd "$(dirname "$0")" && pwd)
SCRIPT=$HERE/../aix.sh
T=$(mktemp -d)
trap 'rm -rf "$T"' 0
FAILED=0

fail() { echo "  FAIL: $*"; FAILED=1; }
ok() { echo "  ok: $*"; }

# check <description> <command...>
check() {
  desc=$1
  shift
  if "$@"; then ok "$desc"; else fail "$desc"; fi
}

# --- fixtures ---------------------------------------------------------------

mkdir -p "$T/cache"
"$PY" - "$T/cache" <<'EOF' || exit 1
import io, json, os, sys, zipfile
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
cache = sys.argv[1]

def wheel(project, version, member, dest):
    meta = json.load(urlopen("https://pypi.org/pypi/%s/%s/json" % (project, version)))
    url = [u["url"] for u in meta["urls"] if u["packagetype"] == "bdist_wheel"][0]
    data = zipfile.ZipFile(io.BytesIO(urlopen(url).read())).read(member)
    open(os.path.join(cache, dest), "wb").write(data)

for v in ("2018.4.16", "2026.4.22", "2026.7.22"):
    wheel("certifi", v, "certifi/cacert.pem", "certifi-%s.pem" % v)
wheel("pip", "21.1.3", "pip/_vendor/certifi/cacert.pem", "pip-21.1.3.pem")
for v in ("2022-04-26", "2025-02-25"):
    data = urlopen("https://curl.se/ca/cacert-%s.pem" % v).read()
    open(os.path.join(cache, "cacert-%s.pem" % v), "wb").write(data)
EOF

# make_install <dir> <pyver> <certifi> <curl cacert>: the layout omnibus builds.
make_install() {
  site=$1/embedded/lib/python$2/site-packages
  mkdir -p "$1/agent" "$1/embedded/bin" "$1/embedded/ssl/certs" "$site/certifi" "$site/pip/_vendor/certifi"
  : > "$1/agent/agent.py"
  ln -s "$(command -v "$PY")" "$1/embedded/bin/python"
  cp "$T/cache/certifi-$3.pem" "$site/certifi/cacert.pem"
  cp "$T/cache/pip-21.1.3.pem" "$site/pip/_vendor/certifi/cacert.pem"
  cp "$T/cache/cacert-$4.pem" "$1/embedded/ssl/certs/cacert.pem"
  ln -s certs/cacert.pem "$1/embedded/ssl/cert.pem"
  chmod 640 "$site/certifi/cacert.pem"
}

bundles() {
  find "$1" -type f -name cacert.pem | sort
}

# Independent of the scrub: parses with the stdlib ssl module.
check_clean() {
  bundles "$1" > "$T/bundles"
  "$PY" - "$T/bundles" <<'EOF'
import hashlib, re, ssl, sys
DISTRUST = {
    "D7A7A0FB5D7E2731D771E9484EBCDEF71D5F0C3E0A2948782BC83EE0EA699EF4",
    "40F6AF0346A99AA1CD1D555A4E9CCE62C7F9634603EE406615833DC8C8D00367",
    "86A1ECBA089C4A8D3BBE2734C612BA341D813E043CF9E8A862CD5C57A36BBE6B",
    "125609AA301DA0A249B97A8239CB6A34216F44DCAC9F3954B14292F2E8C8608F",
    "BC4D809B15189D78DB3E1D8CF4F9726A795DA1643CA5F1358E1DDB0EDC0D7EB3",
}
ANCHOR = "E793C9B02FD8AA13E21C31228ACCB08119643B749C898964B1746D46C3D4CBD2"
bad = 0
for path in open(sys.argv[1]).read().split():
    pems = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                      open(path).read(), re.S)
    fps = set(hashlib.sha256(ssl.PEM_cert_to_DER_cert(p)).hexdigest().upper() for p in pems)
    if fps & DISTRUST or ANCHOR not in fps:
        print("    not clean: %s" % path)
        bad = 1
    # the scrubbed bundle must still load as a trust store
    ssl.create_default_context(cafile=path)
sys.exit(bad)
EOF
}

same_as() {
  for f in $(cd "$2" && bundles .); do
    cmp -s "$1/$f" "$2/$f" || return 1
  done
}

# --- SRC shims --------------------------------------------------------------

mkdir "$T/bin"
cat > "$T/bin/id" <<'EOF'
#!/bin/sh
[ "$1" = -u ] && { echo "${FAKE_UID:-0}"; exit 0; }
exec /usr/bin/id "$@"
EOF
cat > "$T/bin/lssrc" <<'EOF'
#!/bin/sh
[ -n "${FAKE_NO_SRC:-}" ] && { echo "0513-085 The $2 Subsystem is not on file." >&2; exit 1; }
printf 'Subsystem         Group            PID          Status \n %s                     4242         %s\n' "$2" "$(cat "$SHIM_STATE")"
EOF
cat > "$T/bin/stopsrc" <<'EOF'
#!/bin/sh
echo stopsrc >> "$SHIM_CALLS"
echo inoperative > "$SHIM_STATE"
EOF
cat > "$T/bin/startsrc" <<'EOF'
#!/bin/sh
echo startsrc >> "$SHIM_CALLS"
echo active > "$SHIM_STATE"
echo "${FAKE_LOG_LINE:-2026-10-22 10:00:00 UTC | INFO | forwarder | Successfully posted payload to https://unix.agent.datadoghq.com/api/v1/series: (202) {}}" >> "$SHIM_LOG"
EOF
chmod +x "$T/bin/"*
PATH=$T/bin:$PATH
SHIM_STATE=$T/state SHIM_CALLS=$T/calls SHIM_LOG=$T/agent.log
export PATH SHIM_STATE SHIM_CALLS SHIM_LOG

# run <install> <args...>: output in $T/out, exit code in $RC, SRC calls in $CALLS.
run() {
  dir=$1
  shift
  echo active > "$SHIM_STATE"
  : > "$SHIM_CALLS"
  echo "2026-10-22 09:59:00 UTC | INFO | forwarder | old line: possible network issue" > "$SHIM_LOG"
  # $SH unquoted so "bash --posix" works
  # shellcheck disable=SC2086
  $SH "$SCRIPT" -p "$dir" -l "$SHIM_LOG" -w 1 "$@" > "$T/out" 2>&1
  RC=$?
  CALLS=$(tr '\n' ' ' < "$SHIM_CALLS")
}

expect() {
  if [ "$RC" -eq "$1" ] && [ "$CALLS" = "$2" ] && grep -q "$3" "$T/out"; then
    ok "$4"
  else
    fail "$4 (exit $RC, calls '$CALLS')"
    sed 's/^/      /' "$T/out"
  fi
}

backups() {
  find "$1" -name '*.pre-cert-update-*' | wc -l | tr -d ' '
}

mode() {
  "$PY" -c 'import os, sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o777)[-3:])' "$1"
}

# --- per-release scenarios --------------------------------------------------

for release in "1.1.6 3.8 2018.4.16 2022-04-26" \
               "1.3.0 3.10 2026.4.22 2025-02-25" \
               "master 3.8 2026.7.22 2025-02-25"; do
  # shellcheck disable=SC2086
  set -- $release
  echo "== $SH, $1 (certifi $3, cacert $4)"
  A=$T/$1
  make_install "$A" "$2" "$3" "$4"
  cp -Rp "$A" "$T/$1.orig"

  run "$A" -n
  expect 0 "" "3 bundle(s) would be updated" "dry run reports 3 bundles"
  check "dry run wrote nothing" same_as "$A" "$T/$1.orig"

  run "$A"
  expect 0 "stopsrc startsrc " "reached Datadog" "apply restarts once and confirms the intake"
  check "no distrusted root left, anchor present" check_clean "$A"
  check "3 backups" [ "$(backups "$A")" = 3 ]
  check "cert.pem symlink kept" [ -h "$A/embedded/ssl/cert.pem" ]
  check "file mode kept" [ "$(mode "$A/embedded/lib/python$2/site-packages/certifi/cacert.pem")" = 640 ]

  run "$A"
  expect 0 "" "No changes needed" "rerun is a no-op without restart"

  run "$A" -r
  expect 0 "stopsrc startsrc " "restored" "rollback restarts once"
  check "rollback restored original bytes" same_as "$A" "$T/$1.orig"
done

# --- guards and failure paths -----------------------------------------------

echo "== $SH, guards"
G=$T/guard
make_install "$G" 3.8 2026.7.22 2025-02-25
cp -Rp "$G" "$T/guard.orig"

# "VAR=x function" leaks VAR past the call in some shells, so export/unset.
export FAKE_UID=1000
run "$G"
expect 1 "" "must be run as root" "refuses non-root"
unset FAKE_UID

mkdir -p "$T/a7/bin/agent" "$T/a7/embedded"
: > "$T/a7/bin/agent/agent"
run "$T/a7"
expect 1 "" "not a Datadog Unix Agent" "refuses an Agent 7 install"

run "$G" -N
expect 0 "" "Restart the Agent to apply" "-N updates without restarting"
check "-N scrubs" check_clean "$G"
run "$G" -r -N
check "-r -N restores" same_as "$G" "$T/guard.orig"

export FAKE_LOG_LINE="2026-10-22 10:00:00 UTC | ERROR | forwarder | Unable to submit payload to https://unix.agent.datadoghq.com/api/v1/series, possible network issue: SSLError(CERTIFICATE_VERIFY_FAILED)"
run "$G"
expect 3 "stopsrc startsrc " "roll back with" "flags TLS errors logged after the restart"
check "ignores lines logged before the restart" [ -z "$(grep "old line" "$T/out")" ]
run "$G" -r -N

FAKE_LOG_LINE="2026-10-22 10:00:00 UTC | INFO | collector | running check cpu"
run "$G"
expect 3 "stopsrc startsrc " "could not confirm" "warns when no payload reached the intake"
unset FAKE_LOG_LINE
run "$G" -r -N

export FAKE_NO_SRC=1
run "$G"
expect 0 "" "restart the Agent manually" "warns when the SRC subsystem is missing"
unset FAKE_NO_SRC

if [ $FAILED -eq 0 ]; then echo "PASS ($SH)"; else echo "FAILED ($SH)"; fi
exit $FAILED
