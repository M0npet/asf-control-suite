#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FAKEBIN="$TMP/bin"
LOG="$TMP/adb.log"
mkdir -p "$FAKEBIN"

cat > "$FAKEBIN/adb" <<'ADB'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$*" >> "$FAKE_ADB_LOG"

args=("$@")
if [[ "${args[*]}" == *" get-state"* ]]; then
  printf 'device\n'
  exit 0
fi
if [[ "${args[*]}" == *" push "* ]]; then
  exit 0
fi
if [[ "${args[*]}" == *" shell "* ]]; then
  cat >/dev/null || true
  exit 0
fi
printf 'unexpected fake adb invocation: %s\n' "$*" >&2
exit 90
ADB
chmod +x "$FAKEBIN/adb"

run_case() {
  local id="$1"
  local restore="$2"
  : > "$LOG"

  PATH="$FAKEBIN:$PATH" \
  FAKE_ADB_LOG="$LOG" \
  CONTROL_ADB_SERIAL=mock \
  CONTROL_ROLLBACK_CONFIG="$restore" \
  bash "$ROOT/scripts/phone/phone-rollback-via-adb.sh" "$id"

  grep -Fq 'get-state' "$LOG"
  grep -Fq 'push' "$LOG"
  grep -Fq '/data/local/tmp/control-suite-phone-rollback-core.sh' "$LOG"
  grep -Fq "CONTROL_BACKUP_ID='$id'" "$LOG"
  grep -Fq "CONTROL_RESTORE_CONFIG='$restore'" "$LOG"
  grep -Fq 'run-as com.termux' "$LOG"
}

run_case 'test-backup_2026.10.08' 0
run_case 'test-backup_2026.10.08' 1

set +e
PATH="$FAKEBIN:$PATH" \
FAKE_ADB_LOG="$LOG" \
CONTROL_ADB_SERIAL=mock \
bash "$ROOT/scripts/phone/phone-rollback-via-adb.sh" '../escape' >"$TMP/bad.out" 2>"$TMP/bad.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]]
grep -Fq 'invalid backup id' "$TMP/bad.err"

set +e
PATH="$FAKEBIN:$PATH" \
FAKE_ADB_LOG="$LOG" \
CONTROL_ADB_SERIAL=mock \
CONTROL_ROLLBACK_CONFIG=2 \
bash "$ROOT/scripts/phone/phone-rollback-via-adb.sh" 'safe-id' >"$TMP/bad-config.out" 2>"$TMP/bad-config.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]]
grep -Fq 'CONTROL_ROLLBACK_CONFIG must be 0 or 1' "$TMP/bad-config.err"

echo 'PHONE ROLLBACK WRAPPER TEST: PASS'
