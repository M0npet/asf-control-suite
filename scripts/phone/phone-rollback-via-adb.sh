#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CORE="$SCRIPT_DIR/../../installer/phone-rollback-core.sh"
die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ -x "$CORE" ]] || die "rollback core missing: $CORE"
command -v adb >/dev/null 2>&1 || die "adb not found"
BACKUP_ID="${1:-}"
[[ -z "$BACKUP_ID" || "$BACKUP_ID" =~ ^[A-Za-z0-9._-]+$ ]] || die "invalid backup id"
RESTORE_CONFIG="${CONTROL_ROLLBACK_CONFIG:-0}"
[[ "$RESTORE_CONFIG" == 0 || "$RESTORE_CONFIG" == 1 ]] || die "CONTROL_ROLLBACK_CONFIG must be 0 or 1"
SERIAL="${CONTROL_ADB_SERIAL:-}"
if [[ -z "$SERIAL" ]]; then
  mapfile -t devices < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  [[ "${#devices[@]}" -eq 1 ]] || die "expected exactly one authorized ADB device; set CONTROL_ADB_SERIAL"
  SERIAL="${devices[0]}"
fi
adb -s "$SERIAL" get-state | grep -qx device || die "ADB device is not ready"
REMOTE=/data/local/tmp/control-suite-phone-rollback-core.sh
adb -s "$SERIAL" push "$CORE" "$REMOTE" >/dev/null
trap 'adb -s "$SERIAL" shell rm -f "$REMOTE" >/dev/null 2>&1 || true' EXIT

adb -s "$SERIAL" shell \
"run-as com.termux env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin:/system/bin TMPDIR=/data/data/com.termux/files/usr/tmp CONTROL_BACKUP_ID='$BACKUP_ID' CONTROL_RESTORE_CONFIG='$RESTORE_CONFIG' /data/data/com.termux/files/usr/bin/bash -s" <<'PHONE'
set -Eeuo pipefail
SRC=/data/local/tmp/control-suite-phone-rollback-core.sh
STAGE_DIR="$HOME/.cache/asf-control-suite"
STAGE="$STAGE_DIR/control-suite-phone-rollback-core.sh"
mkdir -p "$STAGE_DIR"
cat "$SRC" > "$STAGE"
chmod 0700 "$STAGE"
PD="$PREFIX/bin/proot-distro"
TERMUX_HOME="$HOME"
"$PD" login debian -- /bin/bash -s <<DEBIAN
set -Eeuo pipefail
CORE="$TERMUX_HOME/.cache/asf-control-suite/control-suite-phone-rollback-core.sh"
[[ -x "\$CORE" ]] || { echo "rollback core not visible inside Debian: \$CORE" >&2; exit 30; }
CONTROL_ROLLBACK_CONFIG="$CONTROL_RESTORE_CONFIG" bash "\$CORE" "$CONTROL_BACKUP_ID"
DEBIAN
rm -f "$STAGE"
PHONE

CONTROL_ADB_SERIAL="$SERIAL" bash "$SCRIPT_DIR/phone-verify-via-adb.sh" || true
echo "ROLLBACK COMMAND COMPLETED"
