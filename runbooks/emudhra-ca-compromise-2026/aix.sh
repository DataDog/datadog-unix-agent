#!/bin/sh
# Removes the distrusted eMudhra/emSign roots and the Sectigo "AAA Certificate
# Services" cross-signer from the CA bundles shipped with the Datadog Unix
# Agent, then restarts the Agent so it picks up the cleaned bundles.
#
# AIX /bin/sh is ksh88: keep this POSIX (no local, [[ ]], sed -i, find -print0).
# See README.md next to this file.

set -u

INSTALL_DIR=/opt/datadog-agent
SERVICE=datadog-agent
LOG_FILE=/var/log/datadog/agent.log
# USERTrust RSA Certification Authority, the root the Datadog intake chain
# terminates in once AAA Certificate Services is gone.
ANCHOR_SHA256=E793C9B02FD8AA13E21C31228ACCB08119643B749C898964B1746D46C3D4CBD2
DRY_RUN=false
ROLLBACK=false
RESTART=true
WAIT=60

usage() {
  cat <<EOF
Usage: $0 [-n] [-r] [-N] [-p <install_dir>] [-l <log_file>] [-w <seconds>]
  -n  Dry run: report what would change, write nothing, do not restart.
  -r  Roll back: restore the most recent backup of every bundle, then restart.
  -N  Do not restart the Agent.
  -p  Agent installation directory (default: $INSTALL_DIR).
  -l  Agent log file, if log_file is set in datadog.yaml (default: $LOG_FILE).
  -w  Seconds to watch the log after the restart (default: $WAIT, 0 to skip).
EOF
  exit 1
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

while getopts "nrNp:l:w:h" opt; do
  case $opt in
    n) DRY_RUN=true ;;
    r) ROLLBACK=true ;;
    N) RESTART=false ;;
    p) INSTALL_DIR=$OPTARG ;;
    l) LOG_FILE=$OPTARG ;;
    w) WAIT=$OPTARG ;;
    *) usage ;;
  esac
done

case $WAIT in
  ''|*[!0-9]*) fail "-w expects a number of seconds" ;;
esac
[ "$(id -u)" = 0 ] || fail "must be run as root."
if [ ! -f "$INSTALL_DIR/agent/agent.py" ] || [ ! -d "$INSTALL_DIR/embedded" ]; then
  fail "$INSTALL_DIR is not a Datadog Unix Agent (v1) installation." \
       "Agent 7 is fixed by upgrading it, not by this script."
fi

PY=""
for cand in "$INSTALL_DIR/embedded/bin/python" "$INSTALL_DIR/embedded/bin/python3"; do
  if [ -x "$cand" ] && "$cand" -c "import hashlib, base64, os, sys" >/dev/null 2>&1; then
    PY=$cand
    break
  fi
done
[ -n "$PY" ] || fail "no working Python found under $INSTALL_DIR/embedded/bin."

TMP=${TMPDIR:-/tmp}/dd-emudhra-scrub.$$
trap 'rm -rf "$TMP"' 0
trap 'exit 1' 1 2 15
# mkdir is atomic and fails if the path exists, so nothing can be planted here.
(umask 077 && mkdir "$TMP") || fail "cannot create $TMP"

agent_status() {
  lssrc -s "$SERVICE" 2>/dev/null | awk 'NR == 2 { print $NF }'
}

restart_agent() {
  if [ -z "$(agent_status)" ]; then
    echo "Warning: SRC subsystem $SERVICE not found; restart the Agent manually." >&2
    return 1
  fi
  echo "Restarting $SERVICE..."
  stopsrc -s "$SERVICE" >/dev/null 2>&1
  i=0
  while [ "$(agent_status)" != "inoperative" ]; do
    i=$((i + 1))
    [ $i -gt 30 ] && fail "$SERVICE did not stop within 60s; check it with lssrc -s $SERVICE."
    sleep 2
  done
  startsrc -s "$SERVICE" >/dev/null || fail "startsrc -s $SERVICE failed."
}

# Prints the TLS/connection errors logged after byte offset $1 and exits 0 only
# if a payload reached the intake. The forwarder logs an SSLError as "possible
# network issue". A log shorter than the offset was rotated: read it all.
scan_log() {
  "$PY" - "$LOG_FILE" "$1" <<'EOF'
import os, re, sys
path, offset = sys.argv[1], int(sys.argv[2])
if not os.path.exists(path):
    sys.exit(1)
handle = open(path, "rb")
if os.path.getsize(path) >= offset:
    handle.seek(offset)
error = re.compile(r"CERTIFICATE_VERIFY_FAILED|certificate verify failed|SSLError|possible network issue", re.I)
posted = re.compile(r"Successfully posted payload|API Key invalid")
reached = False
for line in handle.read().decode("latin-1").splitlines():
    if error.search(line):
        print("    " + line)
    elif posted.search(line):
        reached = True
sys.exit(0 if reached else 1)
EOF
}

watch_agent() {
  [ "$WAIT" -gt 0 ] || return 0
  echo "Watching $LOG_FILE for ${WAIT}s..."
  sleep "$WAIT"
  scan_log "$1" > "$TMP/errors"
  reached=$?
  if [ -s "$TMP/errors" ]; then
    echo "The Agent logged connection errors after the restart:" >&2
    cat "$TMP/errors" >&2
    echo "If they are certificate errors, roll back with: $0 -r -p $INSTALL_DIR" >&2
    exit 3
  fi
  if [ "$(agent_status)" != "active" ] || [ $reached -ne 0 ]; then
    echo "Warning: could not confirm that $SERVICE is active and reaching Datadog;" \
         "check lssrc -s $SERVICE and $LOG_FILE." >&2
    exit 3
  fi
  echo "$SERVICE is active and reached Datadog with no connection errors."
}

restore_backups() {
  # Timestamps sort chronologically, so the newest backup is copied last.
  find "$INSTALL_DIR" -type f -name '*.pre-cert-update-*' | sort > "$TMP/backups"
  [ -s "$TMP/backups" ] || fail "no *.pre-cert-update-* backups under $INSTALL_DIR."
  while read -r b; do
    target=${b%%.pre-cert-update-*}
    cp -p "$b" "$target" || fail "cannot restore $target"
    echo "  restored $target from $b"
  done < "$TMP/backups"
}

if [ "$ROLLBACK" = true ]; then
  [ "$DRY_RUN" = true ] && fail "-r and -n cannot be combined."
  echo "=== Restoring CA bundles under $INSTALL_DIR ==="
  restore_backups
  changed=true
else
  cat > "$TMP/anchor.pem" <<'EOF'
-----BEGIN CERTIFICATE-----
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
Q+6IHdfGjjxDah2nGN59PRbxYvnKkKj9
-----END CERTIFICATE-----
EOF

  echo "=== Removing distrusted roots from the CA bundles under $INSTALL_DIR ==="
  echo "Using interpreter: $PY"
  [ "$DRY_RUN" = true ] && echo "Dry run: reporting only, no bundle will be written."

  # Verbatim copy of the scrub in DataDog/dd-agent
  # runbooks/sectigo-root-ca-rotation-2025/linux.sh; keep the two in sync.
  "$PY" - "$INSTALL_DIR" "$TMP/anchor.pem" "$ANCHOR_SHA256" "$DRY_RUN" > "$TMP/scrub.out" 2>&1 <<'PYSCRUB'
import base64, hashlib, os, re, shutil, sys, tempfile, time

# Distrusted following the eMudhra intermediate CA key compromise. The six TLS
# intermediates are cross-signed by Sectigo's "AAA Certificate Services", so
# that root has to go too or the cross-signed path still validates.
DISTRUST = {
    "D7A7A0FB5D7E2731D771E9484EBCDEF71D5F0C3E0A2948782BC83EE0EA699EF4": "AAA Certificate Services",
    "40F6AF0346A99AA1CD1D555A4E9CCE62C7F9634603EE406615833DC8C8D00367": "emSign Root CA - G1",
    "86A1ECBA089C4A8D3BBE2734C612BA341D813E043CF9E8A862CD5C57A36BBE6B": "emSign ECC Root CA - G3",
    "125609AA301DA0A249B97A8239CB6A34216F44DCAC9F3954B14292F2E8C8608F": "emSign Root CA - C1",
    "BC4D809B15189D78DB3E1D8CF4F9726A795DA1643CA5F1358E1DDB0EDC0D7EB3": "emSign ECC Root CA - C3",
}
BUNDLE_NAMES = ("cacert.pem", "ca-certificates.crt", "cacerts.txt")
BLOCK = re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)
MIN_PARSED = 10   # below this we do not treat the file as a trust store

agent_root, anchor_path, expected_fp = sys.argv[1], sys.argv[2], sys.argv[3]
dry_run = (len(sys.argv) > 4 and sys.argv[4] == "true")
agent_real = os.path.realpath(agent_root)

def fingerprint(block):
    body = "".join(l.strip() for l in block.splitlines()[1:-1])
    try:
        return hashlib.sha256(base64.b64decode(body)).hexdigest().upper()
    except Exception:
        return None

try:
    # latin-1, matching the bundle read below. "ascii" with errors="ignore"
    # would silently strip stray bytes and so repair a damaged anchor back
    # into a valid one; the pin must reject such a file, not quietly fix it.
    anchor_text = open(anchor_path, "rb").read().decode("latin-1")
except Exception:
    sys.stderr.write("cannot read %s\n" % anchor_path)
    sys.exit(2)
anchor_blocks = BLOCK.findall(anchor_text)
if not anchor_blocks:
    sys.stderr.write("no certificate found in %s\n" % anchor_path)
    sys.exit(2)
anchor_pem = anchor_blocks[0]
anchor_fp = fingerprint(anchor_pem)

# Pinned: refuse to append anything but the expected anchor.
if anchor_fp != expected_fp:
    found = anchor_fp or "unreadable (the certificate body is not valid base64)"
    sys.stderr.write(
        "%s is not the expected trust anchor\n"
        "  expected SHA-256 %s\n"
        "  found    %s\n"
        "  Refusing to modify any CA bundle.\n"
        % (anchor_path, expected_fp, found))
    sys.exit(2)

stamp = time.strftime("%Y%m%d%H%M%S")
changed = 0
found = 0
skipped = []

def note(path, reason):
    skipped.append((path, reason))

def on_walk_error(err):
    note(getattr(err, "filename", agent_root), "could not be traversed (%s)" % err.strerror)

# os.walk does not follow directory symlinks by default - keep it that way so
# the scrub can never leave the Agent installation directory.
for dirpath, _dirnames, filenames in os.walk(agent_root, followlinks=False, onerror=on_walk_error):
    for name in sorted(filenames):
        if name not in BUNDLE_NAMES:
            continue
        path = os.path.join(dirpath, name)
        found += 1

        # Never rewrite a symlink. Writing through it could modify a file
        # outside the Agent install, and replacing it would silently discard a
        # deliberate link (e.g. an admin pointing a bundle at the OS store).
        if os.path.islink(path):
            note(path, "symlink -> %s" % os.path.realpath(path))
            continue
        if not os.path.realpath(path).startswith(agent_real + os.sep):
            note(path, "resolves outside the Agent install")
            continue

        try:
            # latin-1 maps every byte to one code point, so non-ASCII comment
            # text (accented CA names in the "# Label:" lines) round-trips
            # byte-for-byte. PEM bodies are ASCII either way.
            text = open(path, "rb").read().decode("latin-1")
        except Exception:
            note(path, "not readable")
            continue

        matches = list(BLOCK.finditer(text))
        if not matches:
            continue
        if len(matches) < MIN_PARSED:
            note(path, "only %d certificate(s) - not treated as a trust store" % len(matches))
            continue

        removed = []
        cut = []
        seen = set()
        for m in matches:
            fp = fingerprint(m.group(0))
            if fp in DISTRUST:
                removed.append(DISTRUST[fp])
                cut.append(m.span())
            else:
                seen.add(fp)

        added = anchor_fp not in seen
        if not removed and not added:
            continue

        # Splice out only the distrusted spans so comments, labels and any
        # other non-CERTIFICATE content survive byte-for-byte.
        out, prev = [], 0
        for a, b in cut:
            out.append(text[prev:a])
            prev = b
            while prev < len(text) and text[prev] == "\n":
                prev += 1
        out.append(text[prev:])
        new_text = "".join(out)
        if added:
            if new_text and not new_text.endswith("\n"):
                new_text += "\n"
            new_text += anchor_pem + "\n"

        # Real pre-write validation against the bytes we are about to commit.
        check = BLOCK.findall(new_text)
        check_fps = set(fingerprint(b) for b in check)
        if len(check) != len(matches) - len(removed) + (1 if added else 0):
            note(path, "post-edit certificate count unexpected"); continue
        if check_fps & set(DISTRUST):
            note(path, "a distrusted root survived the edit"); continue
        if anchor_fp not in check_fps:
            note(path, "anchor missing after the edit"); continue

        if dry_run:
            changed += 1
            print("  %s" % path)
            print("    would change %d -> %d certs | would remove: %s%s"
                  % (len(matches), len(check),
                     ", ".join(removed) if removed else "none",
                     " | would append anchor" if added else ""))
            continue

        backup = "%s.pre-cert-update-%s" % (path, stamp)
        tmp = None
        try:
            st = os.stat(path)
            shutil.copy2(path, backup)
            try:
                os.chown(backup, st.st_uid, st.st_gid)
            except Exception:
                pass          # not privileged enough; contents still recoverable
            fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=name + ".", suffix=".tmp")
            handle = os.fdopen(fd, "wb")
            handle.write(new_text.encode("latin-1"))
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            shutil.copymode(path, tmp)
            try:
                os.chown(tmp, st.st_uid, st.st_gid)
            except Exception:
                pass          # not privileged enough; mode still carried over
            os.rename(tmp, path)
            tmp = None
        except Exception:
            for leftover in (tmp, backup):
                if leftover and os.path.exists(leftover):
                    try:
                        os.unlink(leftover)
                    except Exception:
                        pass
            note(path, "could not be rewritten - left untouched")
            continue
        changed += 1

        print("  %s" % path)
        print("    %d -> %d certs | removed: %s%s"
              % (len(matches), len(check),
                 ", ".join(removed) if removed else "none",
                 " | anchor appended" if added else ""))
        print("    backup: %s" % backup)

for path, reason in skipped:
    print("  SKIPPED %s" % path)
    print("    %s - left untouched" % reason)

if found == 0:
    print("  No CA bundles found under %s." % agent_root)
elif changed == 0:
    print("  No changes needed - bundles already clean.")
elif dry_run:
    print("  %d bundle(s) would be updated. Re-run without -n to apply." % changed)
else:
    print("  %d bundle(s) updated." % changed)
if skipped:
    print("  %d bundle(s) skipped (listed above); review them by hand." % len(skipped))
PYSCRUB
  rc=$?
  cat "$TMP/scrub.out"
  [ $rc -eq 0 ] || fail "the scrub failed (exit $rc)."

  changed=false
  grep -q "bundle(s) updated\.$" "$TMP/scrub.out" && changed=true
fi

if [ "$DRY_RUN" = true ] || [ "$RESTART" = false ]; then
  [ "$changed" = true ] && [ "$DRY_RUN" = false ] && echo "Restart the Agent to apply: stopsrc -s $SERVICE; startsrc -s $SERVICE"
  exit 0
fi
if [ "$changed" = false ]; then
  echo "Nothing changed; the Agent was not restarted."
  exit 0
fi

offset=0
[ -f "$LOG_FILE" ] && offset=$(wc -c < "$LOG_FILE" | tr -d ' ')
restart_agent || exit 0
watch_agent "$offset"
