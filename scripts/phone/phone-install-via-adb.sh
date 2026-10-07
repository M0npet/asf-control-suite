#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# shellcheck disable=SC1091
. "$SUITE_ROOT/scripts/build/pins.sh"
load_release_pins "$SUITE_ROOT/release/pins.env"
DIST_NAME="asf-control-suite-v${CONTROL_SUITE_VERSION}-dist"
ARCHIVE_NAME="$DIST_NAME.tar.gz"

ARCHIVE="${1:-}"
[[ -n "$ARCHIVE" && -f "$ARCHIVE" ]] || die "usage: $0 /path/to/$ARCHIVE_NAME"
command -v adb >/dev/null 2>&1 || die "adb not found"
command -v tar >/dev/null 2>&1 || die "tar not found"
command -v sha256sum >/dev/null 2>&1 || die "sha256sum not found"

SERIAL="${CONTROL_ADB_SERIAL:-}"
if [[ -z "$SERIAL" ]]; then
  mapfile -t devices < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  [[ "${#devices[@]}" -eq 1 ]] || die "expected exactly one authorized ADB device; set CONTROL_ADB_SERIAL"
  SERIAL="${devices[0]}"
fi
adb -s "$SERIAL" get-state | grep -qx device || die "ADB device is not ready"

TMP="$(mktemp -d)"
REMOTE="/data/local/tmp/$ARCHIVE_NAME"
trap 'rm -rf "$TMP"; adb -s "$SERIAL" shell rm -f "$REMOTE" >/dev/null 2>&1 || true' EXIT
while IFS= read -r member; do
  [[ "$member" == "$DIST_NAME/"* || "$member" == "$DIST_NAME/" ]] || die "unexpected archive member: $member"
  [[ "$member" != /* && "$member" != *../* && "$member" != ../* ]] || die "unsafe archive member: $member"
done < <(tar -tzf "$ARCHIVE")
tar -xzf "$ARCHIVE" -C "$TMP"
DIST="$TMP/$DIST_NAME"
[[ -d "$DIST" && -s "$DIST/SHA256SUMS" ]] || die "invalid $CONTROL_SUITE_VERSION distribution archive"
unsafe_node="$(find "$DIST" ! -type f ! -type d -print -quit)"
[[ -z "$unsafe_node" ]] || die "archive contains unsupported filesystem node: $unsafe_node"
(cd "$DIST" && sha256sum -c SHA256SUMS)
LOCAL_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
echo "Local archive SHA256: $LOCAL_SHA"

CONTROL_ADB_SERIAL="$SERIAL" bash "$SCRIPT_DIR/phone-preflight-via-adb.sh"

adb -s "$SERIAL" push "$ARCHIVE" "$REMOTE" >/dev/null
REMOTE_SHA="$(adb -s "$SERIAL" shell sha256sum "$REMOTE" | tr -d '\r' | awk '{print $1}')"
[[ "$REMOTE_SHA" == "$LOCAL_SHA" ]] || die "ADB transfer checksum mismatch"

adb -s "$SERIAL" shell \
"run-as com.termux env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin:/system/bin TMPDIR=/data/data/com.termux/files/usr/tmp CONTROL_ARCHIVE_NAME='$ARCHIVE_NAME' CONTROL_DIST_NAME='$DIST_NAME' /data/data/com.termux/files/usr/bin/bash -s" <<'PHONE'
set -Eeuo pipefail
SRC="/data/local/tmp/$CONTROL_ARCHIVE_NAME"
STAGE_DIR="$HOME/.cache/asf-control-suite"
STAGE="$STAGE_DIR/$CONTROL_ARCHIVE_NAME"
mkdir -p "$STAGE_DIR"
cat "$SRC" > "$STAGE"
chmod 0600 "$STAGE"
PD="$PREFIX/bin/proot-distro"
TERMUX_HOME="$HOME"
"$PD" login debian -- env TERMUX_HOME="$TERMUX_HOME" CONTROL_ARCHIVE_NAME="$CONTROL_ARCHIVE_NAME" CONTROL_DIST_NAME="$CONTROL_DIST_NAME" /bin/bash -s <<'DEBIAN'
set -Eeuo pipefail
ARCHIVE="$TERMUX_HOME/.cache/asf-control-suite/$CONTROL_ARCHIVE_NAME"
[[ -r "$ARCHIVE" ]] || { echo "staged archive not visible inside Debian: $ARCHIVE" >&2; exit 30; }
TMP="$(mktemp -d /tmp/asf-control-install.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
tar -xzf "$ARCHIVE" -C "$TMP"
DIST="$TMP/$CONTROL_DIST_NAME"
[[ -x "$DIST/installer/phone-transaction.sh" ]] || { echo "transaction installer missing" >&2; exit 31; }
bash "$DIST/installer/phone-transaction.sh" "$DIST"
DEBIAN
rm -f "$STAGE"
PHONE

CONTROL_ADB_SERIAL="$SERIAL" bash "$SCRIPT_DIR/phone-verify-via-adb.sh"
echo "CONTROL SUITE PHONE INSTALL PASSED"
