# Datadog Unix Agent — Distrusted CA Scrub Runbook (2026 eMudhra compromise)

## Overview

In October 2026, private keys for eight eMudhra/emSign intermediate certificate
authorities were reported compromised and revoked. Six of them are TLS CAs, and
all are cross-signed by Sectigo's **AAA Certificate Services** root, so a trust
store that still carries *either* the emSign roots *or* the AAA cross-signer will
accept certificates minted with the compromised keys.

The Datadog Unix Agent (the AIX Agent, v1.x) ships its **own** CA bundles inside
the package and does not use the operating system trust store. `aix.sh` rewrites
those bundles in place and restarts the Agent.

## Who Is Affected

Every Datadog Unix Agent v1 installation. Each shipped release carries at least
one of the distrusted roots:

| Bundle | 1.1.6 | 1.3.0 (release branch) |
|---|---|---|
| `certifi/cacert.pem` (all Agent HTTP traffic) | AAA | 4 emSign roots |
| `pip/_vendor/certifi/cacert.pem` | AAA + 4 emSign | AAA + 4 emSign |
| `embedded/ssl/certs/cacert.pem` (OpenSSL default) | AAA + 4 emSign | AAA + 4 emSign |

A newer `certifi` alone is not enough: `certifi` 2026.10.19 still carries emSign
G1, C1 and C3.

Agent 7 on AIX also installs to `/opt/datadog-agent`. It is fixed by upgrading it,
and `aix.sh` refuses to run against it.

## Usage

Run as root:

```sh
./aix.sh -n     # preview: reports what would change, writes nothing
./aix.sh        # apply, restart the Agent, watch its log for 60s
```

| Option | Meaning |
|---|---|
| `-n` | Dry run: report what would change, write nothing, do not restart. |
| `-r` | Roll back: restore the most recent backup of every bundle, then restart. |
| `-N` | Do not restart the Agent. |
| `-p <dir>` | Agent installation directory (default `/opt/datadog-agent`). |
| `-l <file>` | Agent log, if `log_file` is set in `datadog.yaml` (default `/var/log/datadog/agent.log`). |
| `-w <seconds>` | How long to watch the log after the restart (default 60, `0` to skip). |

The script is POSIX `sh` (AIX `/bin/sh` is ksh88), and needs nothing beyond the
Agent's embedded Python: no `bash`, `sudo`, `curl` or network access.

Exit codes: `0` success, `1` refused or failed before restarting, `3` the Agent
was restarted but could not be confirmed active and reaching Datadog.

## What the Script Does

1. Removes the distrusted roots — `AAA Certificate Services` plus
   `emSign Root CA - G1`, `emSign ECC Root CA - G3`, `emSign Root CA - C1` and
   `emSign ECC Root CA - C3` — matched by SHA-256 fingerprint, from every
   `cacert.pem` found under the install directory.
2. Ensures each bundle still contains **USERTrust RSA Certification Authority**,
   the root the Datadog intake chain terminates in, appending it if absent.
3. Writes a timestamped backup next to each modified file
   (`<bundle>.pre-cert-update-<YYYYmmddHHMMSS>`).
4. Restarts the `datadog-agent` SRC subsystem, only if a bundle changed.
5. Watches the Agent log and exits `3` if the restarted Agent logs a connection
   error or does not post a payload.

The scrub itself is a verbatim copy of the one in the Agent v5 runbook
([DataDog/dd-agent#3985](https://github.com/DataDog/dd-agent/pull/3985)) and keeps its guarantees: it never leaves the install directory, never rewrites
symlinks, pins the appended anchor by fingerprint, and writes atomically,
preserving file mode and ownership.

### Why removing AAA does not break the intake

`unix.agent.datadoghq.com` and `unix.agent.datadoghq.eu` serve:

```
unix.agent.datadoghq.com <- Sectigo DV R36 <- Sectigo Root R46 <- USERTrust RSA <- AAA Certificate Services
```

USERTrust RSA is in every scrubbed bundle, and the Agent's OpenSSL (1.1.1)
stops at the first trusted certificate, so the chain validates without AAA. The
other sites chain to DigiCert Global Root G2, which is unaffected.

### What else this can affect

The bundles are not Datadog-specific. If an integration target still presents a
chain that depends on the AAA cross-sign, that check will start failing with a
certificate error after the scrub.

## Verification

The eMudhra project publishes a test endpoint signed through the compromised
chain. A scrubbed bundle must reject it:

```sh
for b in $(find /opt/datadog-agent -type f -name cacert.pem); do
  /opt/datadog-agent/embedded/bin/python - "$b" <<'EOF'
import socket, ssl, sys
host = "dv-g3b-aaa-emudhra.we-have-a-problem.com"
ctx = ssl.create_default_context(cafile=sys.argv[1])
try:
    ctx.wrap_socket(socket.create_connection((host, 443), timeout=15), server_hostname=host)
    print("STILL TRUSTED  " + sys.argv[1])
except ssl.SSLError:
    print("rejected       " + sys.argv[1])
EOF
done
```

Every bundle must print `rejected`. The Agent itself should keep reporting.

## Rollback

```sh
./aix.sh -r
```

This copies the newest `*.pre-cert-update-*` backup of every bundle back in
place and restarts the Agent.

## Testing

- `sh tests/test_aix.sh <python> [shell]` runs the script against fake installs
  built from the bundles 1.1.6, 1.3.0 and master ship, with the SRC commands
  stubbed. It covers dry run, apply, idempotency, rollback, mode and symlink
  preservation, the post-restart log check, and the root/Agent 7 guards.
- `sh tests/e2e.sh <ref> <python image> <curl cacert>` runs the real Agent from a
  git ref in a Linux container on OpenSSL 1.1.1, then checks that every regional
  `unix.agent.*` intake still validates with each scrubbed bundle, the
  compromised test chain is rejected, and rollback restores it. For example:
  `sh tests/e2e.sh 1.1.6 python:3.8-bullseye 2022-04-26`.

## Support

Contact [Datadog Support](https://www.datadoghq.com/support/) with your Agent
version, the complete script output, and recent Agent log excerpts.
