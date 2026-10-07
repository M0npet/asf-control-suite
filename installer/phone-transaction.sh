#!/usr/bin/env bash
set -Eeuo pipefail

DIST="${1:-}"
ASF_ROOT="${CONTROL_ASF_ROOT:-/opt/asf}"
PLUGIN_ROOT="$ASF_ROOT/plugins"
BACKUP_ROOT="${CONTROL_BACKUP_ROOT:-$ASF_ROOT/backups/control-suite}"
META_ROOT="$ASF_ROOT/control-suite"
STAMP="${CONTROL_BACKUP_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
BACKUP="$BACKUP_ROOT/$STAMP"
STAGE="$ASF_ROOT/.control-suite-stage-$STAMP"
META_STAGE="$ASF_ROOT/.control-suite-meta-$STAMP"
SKIP_PROCESS="${CONTROL_SKIP_PROCESS:-0}"
TEST_FORCE_FAIL="${CONTROL_TEST_FORCE_FAIL:-0}"
PLUGINS=(PlaytimeGoals AccountManager ControlCenter ControlWeb)
PROC_ROOT="${CONTROL_PROC_ROOT:-/proc}"
MUTATION_STARTED=0
ROLLING_BACK=0
GLOBAL_CONFIG="$ASF_ROOT/config/ASF.json"
ROOT_UI_INDEX="$ASF_ROOT/www/index.html"

say() { printf '\n=== %s ===\n' "$1"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_file() {
  [[ -s "$1" ]] || die "missing required file: $1"
}

assert_phone_headless_config() {
  python3 - "$GLOBAL_CONFIG" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"invalid ASF global config {path}: {exc}")

if not isinstance(data, dict):
    raise SystemExit(f"ASF global config must be a JSON object: {path}")

if data.get("Headless") is not True:
    raise SystemExit(f"phone ASF global config is not Headless=true: {path}")
PY
}

stage_phone_headless_config() {
  local source="$GLOBAL_CONFIG"
  local target="$STAGE/ASF.json"
  local mode=0600

  if [[ -f "$source" ]]; then
    mode="$(stat -c '%a' "$source")"
  fi

  python3 - "$source" "$target" <<'PY'
import json
import os
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])

if source.exists():
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ASF global config must be a JSON object: {source}")
else:
    data = {}

data["Headless"] = True

tmp = target.with_name(target.name + ".tmp")
tmp.write_text(json.dumps(data, ensure_ascii=False, indent="\t") + "\n", encoding="utf-8")
os.replace(tmp, target)
PY

  chmod "$mode" "$target"
}

stage_root_ui_entrypoint() {
  local source="$ROOT_UI_INDEX"
  local target="$STAGE/root-index.html"

  [[ -f "$source" ]] || die "ASF-ui index missing: $source"
  cp -a "$source" "$target"

  python3 - "$target" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = 'data-asf-control-suite-root="1"'

if marker in text:
    raise SystemExit(0)

needle = "<head>"
if needle not in text:
    raise SystemExit(f"cannot patch ASF-ui entrypoint without <head>: {path}")

injected = """<head>
<script data-asf-control-suite-root="1">
const params = new URLSearchParams(window.location.search);
if (params.get('asfui') !== '1') {
  window.location.replace('/Control/' + window.location.search + window.location.hash);
}
</script>"""

path.write_text(
    text.replace(needle, injected, 1),
    encoding="utf-8",
)
PY
}

asf_pids() {
  local cmdline pid argv0
  for cmdline in "$PROC_ROOT"/[0-9]*/cmdline; do
    [[ -r "$cmdline" ]] || continue
    argv0=""
    IFS= read -r -d '' argv0 < "$cmdline" || true
    case "$argv0" in
      ArchiSteamFarm|./ArchiSteamFarm|"$ASF_ROOT/ArchiSteamFarm")
        pid="${cmdline#"$PROC_ROOT"/}"
        pid="${pid%/cmdline}"
        printf '%s\n' "$pid"
        ;;
    esac
  done
}

asf_running() {
  [[ -n "$(asf_pids)" ]]
}

stop_asf_child() {
  [[ "$SKIP_PROCESS" == "1" ]] && return 0
  local pids
  pids="$(asf_pids)"
  [[ -z "$pids" ]] && return 0

  kill -INT $pids 2>/dev/null || true
  for _ in $(seq 1 20); do
    asf_running || return 0
    sleep 1
  done

  pids="$(asf_pids)"
  [[ -z "$pids" ]] && return 0
  kill -TERM $pids 2>/dev/null || true
  for _ in $(seq 1 8); do
    asf_running || return 0
    sleep 1
  done

  return 1
}

base_health() {
  [[ "$SKIP_PROCESS" == "1" ]] && return 0
  local root api
  root="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:1242/ 2>/dev/null || true)"
  api="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:1242/Api/ASF 2>/dev/null || true)"
  [[ "$root" == "200" && "$api" == "401" ]]
}

suite_health() {
  [[ "$SKIP_PROCESS" == "1" ]] && [[ "$TEST_FORCE_FAIL" != "1" ]] && return 0
  [[ "$TEST_FORCE_FAIL" == "1" ]] && return 1

  local control health swagger code
  control="$(curl -sSL -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:1242/Control/ 2>/dev/null || true)"
  health="$(curl -sS -o /tmp/control-suite-health.$$.txt -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/Control/healthz 2>/dev/null || true)"
  code="$(curl -sS -o /tmp/control-suite-swagger.$$.json -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:1242/swagger/ASF/swagger.json 2>/dev/null || true)"
  if [[ "$control" != "200" || "$health" != "200" || "$code" != "200" ]]; then
    echo "Control Suite health gate: control=$control health=$health swagger=$code" >&2
    rm -f /tmp/control-suite-health.$$.txt /tmp/control-suite-swagger.$$.json
    return 1
  fi
  grep -Fq 'control-suite-health' /tmp/control-suite-health.$$.txt || {
    echo 'Control Suite health gate: sentinel missing from /Control/healthz' >&2
    rm -f /tmp/control-suite-health.$$.txt /tmp/control-suite-swagger.$$.json
    return 1
  }
  grep -Fq 'Api/AccountManager' /tmp/control-suite-swagger.$$.json || { rm -f /tmp/control-suite-health.$$.txt /tmp/control-suite-swagger.$$.json; return 1; }
  grep -Fq 'Api/ControlCenter/Status' /tmp/control-suite-swagger.$$.json || { rm -f /tmp/control-suite-health.$$.txt /tmp/control-suite-swagger.$$.json; return 1; }
  grep -Fq 'Api/PlaytimeGoals' /tmp/control-suite-swagger.$$.json || { rm -f /tmp/control-suite-health.$$.txt /tmp/control-suite-swagger.$$.json; return 1; }
  rm -f /tmp/control-suite-health.$$.txt /tmp/control-suite-swagger.$$.json
  return 0
}

wait_for_health() {
  if [[ "$SKIP_PROCESS" == "1" ]]; then
    suite_health
    return $?
  fi
  for _ in $(seq 1 100); do
    if asf_running && base_health && suite_health; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_base_health() {
  [[ "$SKIP_PROCESS" == "1" ]] && return 0
  for _ in $(seq 1 100); do
    if asf_running && base_health; then
      return 0
    fi
    sleep 1
  done
  return 1
}

restore_backup_files() {
  if [[ -f "$BACKUP/ArchiSteamFarm" ]]; then
    cp -a "$BACKUP/ArchiSteamFarm" "$ASF_ROOT/ArchiSteamFarm"
  fi

  for plugin in "${PLUGINS[@]}"; do
    rm -rf "$PLUGIN_ROOT/$plugin"
    if [[ -d "$BACKUP/plugins/$plugin" ]]; then
      cp -a "$BACKUP/plugins/$plugin" "$PLUGIN_ROOT/$plugin"
    fi
  done

  rm -rf "$META_ROOT/installed"
  if [[ -d "$BACKUP/installed-metadata" ]]; then
    mkdir -p "$META_ROOT"
    cp -a "$BACKUP/installed-metadata" "$META_ROOT/installed"
  fi

  if [[ -f "$BACKUP/ASF.json" ]]; then
    cp -a "$BACKUP/ASF.json" "$GLOBAL_CONFIG"
  elif [[ -f "$BACKUP/ASF_CONFIG_ABSENT" ]]; then
    rm -f "$GLOBAL_CONFIG"
  fi

  if [[ -f "$BACKUP/AccountManager.defaults.json" ]]; then
    cp -a "$BACKUP/AccountManager.defaults.json" "$ASF_ROOT/config/AccountManager.defaults.json"
  elif [[ -f "$BACKUP/ACCOUNT_DEFAULTS_ABSENT" ]]; then
    rm -f "$ASF_ROOT/config/AccountManager.defaults.json"
  fi

  if [[ -f "$BACKUP/www/index.html" ]]; then
    mkdir -p "$ASF_ROOT/www"
    cp -a "$BACKUP/www/index.html" "$ROOT_UI_INDEX"
  elif [[ -f "$BACKUP/WWW_INDEX_ABSENT" ]]; then
    rm -f "$ROOT_UI_INDEX"
  fi
}

rollback_now() {
  local reason="$1"
  [[ "$ROLLING_BACK" == "1" ]] && return 1
  ROLLING_BACK=1
  trap - ERR
  set +e
  printf 'ROLLBACK: %s\n' "$reason" >&2
  stop_asf_child
  restore_backup_files
  rm -rf "$STAGE" "$META_STAGE"
  if [[ "$SKIP_PROCESS" != "1" ]]; then
    wait_for_base_health
  fi
  printf 'ROLLBACK COMPLETE: %s\n' "$BACKUP" >&2
  return 1
}

on_error() {
  local code=$?
  if [[ "$MUTATION_STARTED" == "1" ]]; then
    rollback_now "unexpected installer failure (exit $code)" || true
  fi
  exit "$code"
}
trap on_error ERR

say "VALIDATE PAYLOAD"
[[ -d "$DIST" ]] || die "distribution directory not found: $DIST"
unsafe_node="$(find "$DIST" ! -type f ! -type d -print -quit)"
[[ -z "$unsafe_node" ]] || die "distribution contains unsupported filesystem node: $unsafe_node"
require_file "$DIST/SHA256SUMS"
require_file "$DIST/BUILD-METADATA.txt"
require_file "$DIST/ArchiSteamFarm"
[[ -x "$DIST/ArchiSteamFarm" ]] || die "patched ASF runtime is not executable"
for plugin in "${PLUGINS[@]}"; do require_file "$DIST/plugins/$plugin/$plugin.dll"; done
for asset in index.html i18n.js core.js qrcode.min.js qrcode.LICENSE.txt app.js app.css; do require_file "$DIST/plugins/ControlWeb/www/$asset"; done
(
  cd "$DIST"
  sha256sum -c SHA256SUMS
)
grep -Eq '^ASF commit: [0-9a-f]{40}$' "$DIST/BUILD-METADATA.txt" || die "payload ASF commit metadata invalid"
grep -Eq '^PlaytimeGoals commit: [0-9a-f]{40}$' "$DIST/BUILD-METADATA.txt" || die "payload PlaytimeGoals commit metadata invalid"

say "VALIDATE TARGET"
[[ -x "$ASF_ROOT/ArchiSteamFarm" ]] || die "ASF executable missing: $ASF_ROOT/ArchiSteamFarm"
[[ -d "$PLUGIN_ROOT" ]] || die "ASF plugins directory missing: $PLUGIN_ROOT"
[[ -d "$ASF_ROOT/config" ]] || die "ASF config directory missing: $ASF_ROOT/config"
[[ -f "$ROOT_UI_INDEX" ]] || die "ASF-ui index missing: $ROOT_UI_INDEX"
command -v python3 >/dev/null 2>&1 || die "python3 is required to enforce the phone Headless=true invariant"
if [[ -f "$GLOBAL_CONFIG" ]]; then
  python3 -m json.tool "$GLOBAL_CONFIG" >/dev/null || die "ASF global config is not valid JSON: $GLOBAL_CONFIG"
fi
mkdir -p "$BACKUP_ROOT" "$META_ROOT"

say "STAGE"
rm -rf "$STAGE" "$META_STAGE"
mkdir -p "$STAGE/plugins" "$META_STAGE"
cp "$DIST/ArchiSteamFarm" "$STAGE/ArchiSteamFarm"
cp -a "$DIST/plugins/." "$STAGE/plugins/"
stage_phone_headless_config
stage_root_ui_entrypoint
find "$STAGE" -type d -exec chmod 0755 {} +
find "$STAGE" -type f ! -name ASF.json -exec chmod 0644 {} +
chmod 0755 "$STAGE/ArchiSteamFarm"
cp "$DIST/SHA256SUMS" "$DIST/BUILD-METADATA.txt" "$DIST/INSTALL-LAYOUT.txt" "$META_STAGE/"
printf 'BackupId: %s\nInstalledUtc: %s\n' "$STAMP" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$META_STAGE/INSTALL-RECORD.txt"

# Validate staged bytes against payload hashes before the running process is touched.
while IFS= read -r line; do
  expected="${line%% *}"
  rel="${line#*  }"
  case "$rel" in
    ArchiSteamFarm|plugins/*) ;;
    *) continue ;;
  esac
  actual="$(sha256sum "$STAGE/$rel" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || die "staged checksum mismatch: $rel"
done < "$DIST/SHA256SUMS"

say "BACKUP CURRENT INSTALL"
mkdir -p "$BACKUP/plugins" "$BACKUP/www"
cp -a "$ASF_ROOT/ArchiSteamFarm" "$BACKUP/ArchiSteamFarm"
for plugin in "${PLUGINS[@]}"; do
  if [[ -d "$PLUGIN_ROOT/$plugin" ]]; then
    cp -a "$PLUGIN_ROOT/$plugin" "$BACKUP/plugins/$plugin"
  else
    : > "$BACKUP/ABSENT.$plugin"
  fi
done
if [[ -d "$META_ROOT/installed" ]]; then
  cp -a "$META_ROOT/installed" "$BACKUP/installed-metadata"
else
  : > "$BACKUP/INSTALLED_METADATA_ABSENT"
fi
if [[ -f "$GLOBAL_CONFIG" ]]; then
  cp -a "$GLOBAL_CONFIG" "$BACKUP/ASF.json"
else
  : > "$BACKUP/ASF_CONFIG_ABSENT"
fi
if [[ -f "$ASF_ROOT/config/AccountManager.defaults.json" ]]; then
  cp -a "$ASF_ROOT/config/AccountManager.defaults.json" "$BACKUP/AccountManager.defaults.json"
else
  : > "$BACKUP/ACCOUNT_DEFAULTS_ABSENT"
fi
if [[ -f "$ROOT_UI_INDEX" ]]; then
  cp -a "$ROOT_UI_INDEX" "$BACKUP/www/index.html"
else
  : > "$BACKUP/WWW_INDEX_ABSENT"
fi
(
  cd "$BACKUP"
  find . -type f ! -name PREINSTALL.sha256 -print0 | sort -z | xargs -0 -r sha256sum > PREINSTALL.sha256
)
printf '%s\n' "$STAMP" > "$BACKUP_ROOT/LAST_BACKUP"

say "COMMIT PHONE HEADLESS CONFIG"
MUTATION_STARTED=1
mv "$STAGE/ASF.json" "$GLOBAL_CONFIG"
assert_phone_headless_config

# Commit Headless=true before stopping the child. The phone supervisor may
# respawn ASF immediately after SIGINT/SIGTERM; any such process must observe
# the headless invariant from its first instruction rather than racing the
# runtime/plugin swap with the old interactive global config.
say "STOP ASF CHILD"
stop_asf_child || die "could not stop ArchiSteamFarm child safely"

say "COMMIT DEFAULT WEB UI ENTRYPOINT"
mv "$STAGE/root-index.html" "$ROOT_UI_INDEX"
grep -Fq 'data-asf-control-suite-root="1"' "$ROOT_UI_INDEX" || die "default Control Suite entrypoint marker missing"

say "COMMIT RUNTIME + PLUGIN SWAP"
mv "$STAGE/ArchiSteamFarm" "$ASF_ROOT/ArchiSteamFarm"
for plugin in "${PLUGINS[@]}"; do
  rm -rf "$PLUGIN_ROOT/$plugin"
  mv "$STAGE/plugins/$plugin" "$PLUGIN_ROOT/$plugin"
done
rm -rf "$META_ROOT/installed"
mv "$META_STAGE" "$META_ROOT/installed"
printf '%s\n' "$STAMP" > "$META_ROOT/installed/LAST_BACKUP"
rm -rf "$STAGE"

say "VERIFY INSTALLED BYTES"
while IFS= read -r line; do
  expected="${line%% *}"
  rel="${line#*  }"
  case "$rel" in
    ArchiSteamFarm|plugins/*) ;;
    *) continue ;;
  esac
  actual="$(sha256sum "$ASF_ROOT/$rel" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || { rollback_now "installed checksum mismatch: $rel"; exit 20; }
done < "$DIST/SHA256SUMS"

say "VERIFY PHONE HEADLESS CONFIG"
assert_phone_headless_config

say "WAIT FOR ASF + CONTROL HEALTH"
if ! wait_for_health; then
  rollback_now "post-install health gate failed" || true
  exit 21
fi

MUTATION_STARTED=0
trap - ERR
say "INSTALL PASSED"
printf 'Backup: %s\n' "$BACKUP"
printf 'Installed metadata: %s\n' "$META_ROOT/installed"
printf 'Control UI: / (default) -> /Control/\n'
