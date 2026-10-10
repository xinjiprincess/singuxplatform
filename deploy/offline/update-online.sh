#!/bin/sh
# Fetch data only; execute the reviewed updater already installed on this host.
set -eu
umask 077
die() { echo "$*" >&2; exit 1; }
[ "$#" -eq 3 ] || die 'Usage: sh update-online.sh DEPLOY_DIR MANIFEST_HTTPS_URL EXPECTED_SHA256'
deployment=$(CDPATH= cd -- "$1" && pwd)
url=$2
checksum=$3
case "$url" in https://*) ;; *) die 'Release manifest requires HTTPS.' ;; esac
printf '%s\n' "$checksum" | grep -Eq '^[a-f0-9]{64}$' || die 'A trusted release SHA256 is required.'
for cmd in curl jq sha256sum mktemp; do command -v "$cmd" >/dev/null || die "Missing command: $cmd"; done
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
release=$(mktemp -d)
cleanup() { rm -f "$release/update.json"; rmdir "$release"; }
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 15 --max-time 120 --max-filesize 1048576 \
  --output "$release/update.json" "$url"
[ "$(sha256sum "$release/update.json" | cut -d ' ' -f1)" = "$checksum" ] || die 'Release manifest checksum mismatch.'
jq -e '.mode == "online"' "$release/update.json" >/dev/null || die 'Expected an online release manifest.'
sh "$script_dir/update.sh" "$deployment" "$release"
