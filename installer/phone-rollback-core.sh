#!/usr/bin/env bash
set -Eeuo pipefail

ASF_ROOT="${CONTROL_ASF_ROOT:-/opt/asf}"
BACKUP_ROOT="${CONTROL_BACKUP_ROOT:-$ASF_ROOT/backups/control-suite}"
BACKUP_ID="${1:-}"
SKIP_PROCESS="${CONTROL_SKIP_PROCESS:-0}"
RESTORE_CONFIG="${CONTROL_ROLLBACK_CONFIG:-0}"
PLUGINS=(PlaytimeGoals AccountManager ControlCenter ControlWeb)
PROC_ROOT="${CONTROL_PROC_ROOT:-/proc}"
GLOBAL_CONFIG="$ASF_ROOT/config/ASF.json"

[[ -n "$BACKUP_ID" ]] || BACKUP_ID="$(cat "$BACKUP_ROOT/LAST_BACKUP" 2>/dev/null || true)"
[[ -n "$BACKUP_ID" ]] || { echo "no backup id supplied and LAST_BACKUP is unavailable" >&2; exit 2; }
BACKUP="$BACKUP_ROOT/$BACKUP_ID"
[[ -d "$BACKUP" ]] || { echo "backup not found: $BACKUP" >&2; exit 3; }

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
  for _ in $(seq 1 20); do asf_running || return 0; sleep 1; done
  pids="$(asf_pids)"
  [[ -z "$pids" ]] && return 0
  kill -TERM $pids 2>/dev/null || true
  for _ in $(seq 1 8); do asf_running || return 0; sleep 1; done
  return 1
}

wait_base() {
  [[ "$SKIP_PROCESS" == "1" ]] && return 0
  for _ in $(seq 1 100); do
    root="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:1242/ 2>/dev/null || true)"
    api="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:1242/Api/ASF 2>/dev/null || true)"
    if asf_running && [[ "$root" == 200 && "$api" == 401 ]]; then return 0; fi
    sleep 1
  done
  return 1
}

stop_asf_child || { echo "could not stop ASF child" >&2; exit 4; }
mkdir -p "$ASF_ROOT/plugins" "$ASF_ROOT/control-suite"
[[ -s "$BACKUP/ArchiSteamFarm" ]] || { echo "backup ASF core missing" >&2; exit 6; }
cp -a "$BACKUP/ArchiSteamFarm" "$ASF_ROOT/ArchiSteamFarm"

for plugin in "${PLUGINS[@]}"; do
  rm -rf "$ASF_ROOT/plugins/$plugin"
  if [[ -d "$BACKUP/plugins/$plugin" ]]; then
    cp -a "$BACKUP/plugins/$plugin" "$ASF_ROOT/plugins/$plugin"
  fi
done

rm -rf "$ASF_ROOT/control-suite/installed"
if [[ -d "$BACKUP/installed-metadata" ]]; then
  cp -a "$BACKUP/installed-metadata" "$ASF_ROOT/control-suite/installed"
fi

if [[ -f "$BACKUP/ASF.json" ]]; then
  cp -a "$BACKUP/ASF.json" "$GLOBAL_CONFIG"
elif [[ -f "$BACKUP/ASF_CONFIG_ABSENT" ]]; then
  rm -f "$GLOBAL_CONFIG"
fi

if [[ "$RESTORE_CONFIG" == "1" ]]; then
  if [[ -f "$BACKUP/AccountManager.defaults.json" ]]; then
    cp -a "$BACKUP/AccountManager.defaults.json" "$ASF_ROOT/config/AccountManager.defaults.json"
  elif [[ -f "$BACKUP/ACCOUNT_DEFAULTS_ABSENT" ]]; then
    rm -f "$ASF_ROOT/config/AccountManager.defaults.json"
  fi
fi

wait_base || { echo "rollback files restored but ASF base health did not recover" >&2; exit 5; }
printf 'ROLLBACK PASSED\nBackup: %s\nASF global config restored: yes\nAccountManager defaults restored: %s\n' "$BACKUP" "$RESTORE_CONFIG"
