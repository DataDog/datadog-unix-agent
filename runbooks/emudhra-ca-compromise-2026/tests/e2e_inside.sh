#!/bin/sh
# Container side of e2e.sh: /src is the Agent source, /runbook this directory.

set -u

D=/opt/datadog-agent
LOG=/var/log/datadog/agent.log
FAILED=0

step() { printf '\n### %s\n' "$*"; }
fail() { echo "FAIL: $*"; FAILED=1; }

step "Installing the Agent into $D"
python -m venv "$D/embedded"
"$D/embedded/bin/pip" install -q --disable-pip-version-check pip==21.1.3 || exit 1
# Old sdists: PyYAML 5.4 (1.1.6) needs Cython < 3, cryptography 2.8 (1.3.0)
# needs pkg_resources.
printf 'cython<3\nsetuptools<70\n' > /tmp/constraints.txt
PIP_CONSTRAINT=/tmp/constraints.txt "$D/embedded/bin/pip" install -q --disable-pip-version-check -r /src/requirements.txt || exit 1
# 1.1.6 calls platform.dist() (gone in Python 3.8) on Linux only; AIX never does.
echo 'import platform; platform.dist = getattr(platform, "dist", lambda: ("", "", ""))' \
  > "$("$D/embedded/bin/python" -c 'import site; print(site.getsitepackages()[0])')/sitecustomize.py"
cp -R /src "$D/agent"
mkdir -p "$D/embedded/ssl/certs" "$D/run" /etc/datadog-agent /var/log/datadog
curl -sSf -o "$D/embedded/ssl/certs/cacert.pem" "https://curl.se/ca/cacert-$CACERT.pem" || exit 1
ln -s certs/cacert.pem "$D/embedded/ssl/cert.pem"
printf 'api_key: deadbeefdeadbeefdeadbeefdeadbeef\nhostname: emudhra-runbook-e2e\n' > /etc/datadog-agent/datadog.yaml
"$D/embedded/bin/python" -c 'import ssl, requests, urllib3, certifi; print(ssl.OPENSSL_VERSION, "| requests", requests.__version__, "| urllib3", urllib3.__version__, "| certifi", certifi.__version__)'

# SRC stand-ins. SSL_CERT_FILE plays the role of the embedded OpenSSL's OPENSSLDIR.
cat > /usr/local/bin/startsrc <<'EOF'
#!/bin/sh
cd /opt/datadog-agent/agent || exit 1
SSL_CERT_FILE=/opt/datadog-agent/embedded/ssl/cert.pem nohup /opt/datadog-agent/embedded/bin/python agent.py -m start >/dev/null 2>&1 &
echo $! > /tmp/agent.pid
EOF
cat > /usr/local/bin/stopsrc <<'EOF'
#!/bin/sh
kill "$(cat /tmp/agent.pid)"
EOF
cat > /usr/local/bin/lssrc <<'EOF'
#!/bin/sh
status=inoperative
[ -f /tmp/agent.pid ] && kill -0 "$(cat /tmp/agent.pid)" 2>/dev/null && status=active
printf 'Subsystem         Group            PID          Status \n %s                                  %s\n' "$2" "$status"
EOF
chmod +x /usr/local/bin/startsrc /usr/local/bin/stopsrc /usr/local/bin/lssrc

# probe trusted|rejected: every intake must validate with every bundle; the
# compromised test chain must match the expectation.
probe() {
  SSL_CERT_FILE=$D/embedded/ssl/cert.pem "$D/embedded/bin/python" - "$1" <<'EOF'
import glob, socket, ssl, sys
import certifi, requests

SITES = ["datadoghq.com", "datadoghq.eu", "us3.datadoghq.com", "us5.datadoghq.com",
         "ap1.datadoghq.com", "ap2.datadoghq.com", "ddog-gov.com"]
EMUDHRA = "dv-g3b-aaa-emudhra.we-have-a-problem.com"
expect = sys.argv[1]
bundles = {
    "certifi": certifi.where(),
    "embedded": "/opt/datadog-agent/embedded/ssl/certs/cacert.pem",
    "pip": glob.glob("/opt/datadog-agent/embedded/lib/python*/site-packages/pip/_vendor/certifi/cacert.pem")[0],
}

def handshake(host, cafile):
    ctx = ssl.create_default_context(cafile=cafile)
    try:
        with socket.create_connection((host, 443), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                return None
    except ssl.SSLError as e:
        return str(e)

bad = 0
for site in SITES:
    host = "unix.agent." + site
    for name, path in sorted(bundles.items()):
        err = handshake(host, path)
        if err:
            bad = 1
            print("  FAIL %-30s %-8s %s" % (host, name, err))
    try:
        # What the forwarder does: requests with its default (certifi) verification.
        code = requests.post("https://%s/api/v1/series?api_key=0" % host, data="{}", timeout=15).status_code
        print("  ok   %-30s TLS ok with all bundles, forwarder-style POST -> HTTP %d" % (host, code))
    except requests.exceptions.SSLError as e:
        bad = 1
        print("  FAIL %-30s requests: %s" % (host, e))

trusted = [name for name, path in sorted(bundles.items()) if handshake(EMUDHRA, path) is None]
print("  %s trusted by: %s" % (EMUDHRA, ", ".join(trusted) or "none"))
if expect == "rejected" and trusted:
    bad = 1
    print("  FAIL the compromised chain is still trusted")
if expect == "trusted" and not trusted:
    bad = 1
    print("  FAIL expected at least one unscrubbed bundle to trust the compromised chain")
sys.exit(bad)
EOF
}

forwarder_lines() {
  grep -cE "Successfully posted payload|API Key invalid" "$LOG"
}

step "Baseline: Agent running on the shipped bundles"
startsrc -s datadog-agent
sleep 40
lssrc -s datadog-agent
[ "$(forwarder_lines)" -gt 0 ] || fail "the Agent never reached the intake before the scrub"
grep -E "possible network issue|SSLError" "$LOG" && fail "connection errors before the scrub"
probe trusted || fail "baseline probe"

step "Dry run"
sh /runbook/aix.sh -n || fail "dry run exited $?"

step "Scrub and restart"
sh /runbook/aix.sh -w 40
rc=$?
[ $rc -eq 0 ] || fail "aix.sh exited $rc"
tail -n 3 "$LOG"
probe rejected || fail "post-scrub probe"

step "Rollback"
sh /runbook/aix.sh -r -w 40
rc=$?
[ $rc -eq 0 ] || fail "aix.sh -r exited $rc"
probe trusted || fail "post-rollback probe"

stopsrc -s datadog-agent
echo
if [ $FAILED -eq 0 ]; then echo "E2E PASS"; else echo "E2E FAILED"; fi
exit $FAILED
