#!/usr/bin/env bash
set -Eeuo pipefail

die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v adb >/dev/null 2>&1 || die "adb not found"
SERIAL="${CONTROL_ADB_SERIAL:-}"
if [[ -z "$SERIAL" ]]; then
  mapfile -t devices < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  [[ "${#devices[@]}" -eq 1 ]] || die "expected exactly one authorized ADB device; set CONTROL_ADB_SERIAL"
  SERIAL="${devices[0]}"
fi
adb -s "$SERIAL" get-state | grep -qx device || die "ADB device is not ready"

echo "=== ADB ==="
adb -s "$SERIAL" devices -l 2>/dev/null || true

echo "=== TERMUX SUPERVISORS ==="
adb -s "$SERIAL" shell \
"run-as com.termux env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin:/system/bin TMPDIR=/data/data/com.termux/files/usr/tmp /data/data/com.termux/files/usr/bin/bash -s" <<'PHONE'
set -Eeuo pipefail
for session in asf asf-proxy tailscale-watch; do
  if tmux has-session -t "$session" 2>/dev/null; then echo "$session: present"; else echo "$session: missing (warning)"; fi
done

echo "=== DEBIAN / ASF ==="
PD="$PREFIX/bin/proot-distro"
[[ -x "$PD" ]] || { echo "proot-distro missing" >&2; exit 10; }
"$PD" login debian -- /bin/bash -s <<'DEBIAN'
set -Eeuo pipefail
ASF=/opt/asf
[[ -x "$ASF/ArchiSteamFarm" ]] || { echo "missing $ASF/ArchiSteamFarm" >&2; exit 11; }
[[ -d "$ASF/plugins" && -d "$ASF/config" ]] || { echo "ASF layout incomplete" >&2; exit 12; }
echo "ASF process:"; pgrep -af ArchiSteamFarm || true
echo "Filesystem:"; df -h "$ASF" | tail -n 1
echo "PlaytimeGoals:"; if [[ -f "$ASF/plugins/PlaytimeGoals/PlaytimeGoals.dll" ]]; then sha256sum "$ASF/plugins/PlaytimeGoals/PlaytimeGoals.dll"; else echo "missing (will be installed by release bundle)"; fi
root="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/ 2>/dev/null || true)"
api="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/Api/ASF 2>/dev/null || true)"
echo "IPC root=$root (expected 200)"
echo "IPC unauth API=$api (expected 401)"
[[ "$root" == 200 && "$api" == 401 ]] || { echo "ASF IPC baseline is not healthy" >&2; exit 13; }
DEBIAN
PHONE

echo "PREFLIGHT PASSED (read-only)"
