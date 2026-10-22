#!/bin/sh
# Runs a real Unix Agent from <ref> in a Linux container (OpenSSL 1.1.1, like
# the AIX builds), applies aix.sh and checks the Agent still reaches the
# Datadog intake while the compromised test chain is rejected.
#
# Usage: sh tests/e2e.sh <git ref> <python image> <curl cacert version>
#   sh tests/e2e.sh 1.1.6 python:3.8-bullseye 2022-04-26
#   sh tests/e2e.sh origin/ian.bucad/release_1.3.0 python:3.10-bullseye 2025-02-25

set -eu

REF=${1:?usage: $0 <git ref> <python image> <curl cacert version>}
IMAGE=${2:?}
CACERT=${3:?}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(git -C "$HERE" rev-parse --show-toplevel)
SRC=$(mktemp -d)
trap 'rm -rf "$SRC"' 0

git -C "$REPO" archive "$REF" | tar -x -C "$SRC"
# --init reaps the stopped Agent, otherwise its zombie still looks alive to kill -0.
docker run --rm --init \
  -v "$SRC:/src:ro" \
  -v "$HERE/..:/runbook:ro" \
  -e CACERT="$CACERT" \
  "$IMAGE" sh /runbook/tests/e2e_inside.sh
