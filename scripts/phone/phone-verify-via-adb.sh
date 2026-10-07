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

adb -s "$SERIAL" shell \
"run-as com.termux env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin:/system/bin TMPDIR=/data/data/com.termux/files/usr/tmp /data/data/com.termux/files/usr/bin/bash -s" <<'PHONE'
set -Eeuo pipefail
for session in asf asf-proxy tailscale-watch; do
  if tmux has-session -t "$session" 2>/dev/null; then echo "$session: present"; else echo "$session: missing (warning)"; fi
done
PD="$PREFIX/bin/proot-distro"
"$PD" login debian -- /bin/bash -s <<'DEBIAN'
set -Eeuo pipefail
ASF=/opt/asf
META="$ASF/control-suite/installed"
[[ -d "$META" && -s "$META/SHA256SUMS" && -s "$META/BUILD-METADATA.txt" ]] || { echo "installed metadata missing" >&2; exit 20; }
ASF_PROC=0
for cmdline in /proc/[0-9]*/cmdline; do
  [[ -r "$cmdline" ]] || continue
  argv0=""
  IFS= read -r -d '' argv0 < "$cmdline" || true
  case "$argv0" in
    ArchiSteamFarm|./ArchiSteamFarm|/opt/asf/ArchiSteamFarm) ASF_PROC=1; break ;;
  esac
done
[[ "$ASF_PROC" == "1" ]] || { echo "ArchiSteamFarm process missing" >&2; exit 21; }

while IFS= read -r line; do
  expected="${line%% *}"
  rel="${line#*  }"
  case "$rel" in
    ArchiSteamFarm|plugins/*) ;;
    *) continue ;;
  esac
  [[ -f "$ASF/$rel" ]] || { echo "installed file missing: $rel" >&2; exit 22; }
  actual="$(sha256sum "$ASF/$rel" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || { echo "installed checksum mismatch: $rel" >&2; exit 23; }
done < "$META/SHA256SUMS"

[[ -x "$ASF/ArchiSteamFarm" ]] || { echo "installed ASF runtime is not executable" >&2; exit 29; }

python3 - "$ASF/config/ASF.json" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"invalid ASF global config {path}: {exc}")

if not isinstance(data, dict) or data.get("Headless") is not True:
    raise SystemExit(f"phone ASF global config must contain Headless=true: {path}")

print("headless=true")
PY

root="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/ 2>/dev/null || true)"
api="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/Api/ASF 2>/dev/null || true)"
control="$(curl -sSL -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/Control/ 2>/dev/null || true)"
health_file="$(mktemp)"
health="$(curl -sS -o "$health_file" -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/Control/healthz 2>/dev/null || true)"
swagger_file="$(mktemp)"; trap 'rm -f "$health_file" "$swagger_file"' EXIT
swagger="$(curl -sS -o "$swagger_file" -w '%{http_code}' --connect-timeout 4 http://127.0.0.1:1242/swagger/ASF/swagger.json 2>/dev/null || true)"
echo "root=$root api=$api control=$control health=$health swagger=$swagger"
[[ "$root" == 200 && "$api" == 401 && "$control" == 200 && "$health" == 200 && "$swagger" == 200 ]] || exit 24
grep -Fq 'control-suite-health' "$health_file" || exit 28
grep -Fq 'Api/AccountManager' "$swagger_file" || exit 25
grep -Fq 'Api/ControlCenter/Status' "$swagger_file" || exit 26
grep -Fq 'Api/PlaytimeGoals' "$swagger_file" || exit 27

echo "--- BUILD METADATA ---"
cat "$META/BUILD-METADATA.txt"
echo "--- INSTALL RECORD ---"
cat "$META/INSTALL-RECORD.txt"
echo "PHONE VERIFY PASSED"
DEBIAN
PHONE

if [[ -n "${CONTROL_HTTPS_URL:-}" ]]; then
  base="${CONTROL_HTTPS_URL%/}"
  echo "=== OPTIONAL REMOTE HTTPS ==="
  root="$(curl -ksS -o /dev/null -w '%{http_code}' --connect-timeout 5 "$base/" || true)"
  api="$(curl -ksS -o /dev/null -w '%{http_code}' --connect-timeout 5 "$base/Api/ASF" || true)"
  control="$(curl -ksSL -o /dev/null -w '%{http_code}' --connect-timeout 5 "$base/Control/" || true)"
  echo "https root=$root api=$api control=$control"
  [[ "$root" == 200 && "$api" == 401 && "$control" == 200 ]] || die "remote HTTPS verification failed"
fi
