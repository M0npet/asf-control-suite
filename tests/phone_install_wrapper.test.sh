#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# shellcheck disable=SC1091
. "$ROOT/scripts/build/pins.sh"
load_release_pins "$ROOT/release/pins.env"

DIST_NAME="asf-control-suite-v${CONTROL_SUITE_VERSION}-dist"
ARCHIVE_NAME="$DIST_NAME.tar.gz"
DIST="$TMP/$DIST_NAME"
mkdir -p "$DIST"
printf 'payload\n' > "$DIST/payload.txt"
(
  cd "$DIST"
  sha256sum payload.txt > SHA256SUMS
)
tar -czf "$TMP/$ARCHIVE_NAME" -C "$TMP" "$DIST_NAME"

LOCAL_SHA="$(sha256sum "$TMP/$ARCHIVE_NAME" | awk '{print $1}')"
FAKEBIN="$TMP/bin"
LOG="$TMP/adb.log"
mkdir -p "$FAKEBIN"

cat > "$FAKEBIN/adb" <<'ADB'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%q ' "$@" >> "$FAKE_ADB_LOG"
printf '\n' >> "$FAKE_ADB_LOG"

args=("$@")
if [[ "${args[*]}" == *" get-state"* ]]; then
  printf 'device\n'
  exit 0
fi
if [[ "${args[*]}" == *" devices -l"* ]]; then
  printf 'List of devices attached\nmock device product:mock model:mock device:mock\n'
  exit 0
fi
if [[ "${args[*]}" == *" shell sha256sum "* ]]; then
  printf '%s  %s\n' "$FAKE_ADB_REMOTE_SHA" "${args[-1]}"
  exit 0
fi
if [[ "${args[*]}" == *" shell "* ]]; then
  cat >/dev/null || true
  exit 0
fi
if [[ "${args[*]}" == *" push "* ]]; then
  exit 0
fi
printf 'unexpected fake adb invocation: %q ' "$@" >&2
printf '\n' >&2
exit 90
ADB
chmod +x "$FAKEBIN/adb"

PATH="$FAKEBIN:$PATH" \
FAKE_ADB_LOG="$LOG" \
FAKE_ADB_REMOTE_SHA="$LOCAL_SHA" \
CONTROL_ADB_SERIAL=mock \
bash "$ROOT/scripts/phone/phone-install-via-adb.sh" "$TMP/$ARCHIVE_NAME"

grep -Fq "$ARCHIVE_NAME" "$LOG"
grep -Fq "CONTROL_ARCHIVE_NAME='$ARCHIVE_NAME'" "$LOG"
grep -Fq "CONTROL_DIST_NAME='$DIST_NAME'" "$LOG"
! grep -Fq 'asf-control-suite-v1.0-dist' "$LOG"

OLD_DIST="$TMP/asf-control-suite-v1.0-dist"
mkdir -p "$OLD_DIST"
printf 'payload\n' > "$OLD_DIST/payload.txt"
(
  cd "$OLD_DIST"
  sha256sum payload.txt > SHA256SUMS
)
tar -czf "$TMP/old.tar.gz" -C "$TMP" asf-control-suite-v1.0-dist

set +e
PATH="$FAKEBIN:$PATH" \
FAKE_ADB_LOG="$LOG" \
FAKE_ADB_REMOTE_SHA="$LOCAL_SHA" \
CONTROL_ADB_SERIAL=mock \
bash "$ROOT/scripts/phone/phone-install-via-adb.sh" "$TMP/old.tar.gz" >"$TMP/old.out" 2>"$TMP/old.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]]
grep -Fq 'unexpected archive member: asf-control-suite-v1.0-dist/' "$TMP/old.err"

echo 'PHONE INSTALL WRAPPER TEST: PASS'
