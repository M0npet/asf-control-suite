#!/usr/bin/env bash
# V3 EXPERIMENTAL OPERATOR TOOL; not approved for live operation.
# --run additionally requires deliberate typed authorization.
# Not part of the release artifact. Run on the MINISFORUM V3 tablet.
set -Eeuo pipefail
umask 077

MODE="${1:---precheck}"
case "$MODE" in --precheck|--run) ;; *) echo 'Usage: bash phone-guarded-rollback-v3.sh [--precheck|--run]' >&2; exit 2;; esac
if [[ "$MODE" == '--run' && "${ASFC_LIVE_CONFIRMATION:-}" != 'I_ACCEPT_ASF_DOWNTIME' ]]; then
  echo 'LIVE_CONFIRMATION_REQUIRED; NOT STARTED'
  exit 2
fi
# SAFETY GATE: the actual Mi Max 2 Termux:Boot script also restarts
# asf-proxy. Never call it during ASF-only rollback until the restart
# mechanism is isolated, reviewed and verified. No bypass is provided.
if [[ "$MODE" == '--run' ]]; then
  echo 'ASF_ONLY_RECOVERY_REQUIRED; LIVE_RUN_DISABLED; NOT STARTED' >&2
  exit 40
fi
ROOT="${ASFC_WORK_ROOT:-$HOME/Downloads/asf-v11-6FU4n0}"
SOURCE="$ROOT/source"
BACKUP_ID="${ASFC_BACKUP_ID:-20261008T135623Z-6531}"
# Backup ID enters remote shell context: validate strictly before accessing ADB.
if [[ ! "$BACKUP_ID" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9]+$ || ${#BACKUP_ID} -gt 64 ]]; then
  echo 'INVALID_BACKUP_ID; NOT STARTED' >&2
  exit 2
fi
EXPECTED_ARCHIVE_SHA="${ASFC_EXPECTED_ARCHIVE_SHA:-1decc710627642483f437ac839390ad9052e661d82b6ba4f9973d7005f71c89c}"
EXPECTED_COMMIT="${ASFC_EXPECTED_COMMIT:-6758b79ec17d17975e44aae3891de6a0f084b47e}"
ARCHIVE="$ROOT/artifact/asf-control-suite-v1.1.0-dist.tar.gz"
CORE="$SOURCE/installer/phone-rollback-core.sh"

for app in adb git sha256sum; do command -v "$app" >/dev/null || { echo "MISSING_TOOL=$app"; exit 3; }; done
[[ -r "$ARCHIVE" && -r "$CORE" ]] || { echo 'MISSING_CANDIDATE_OR_CORE'; exit 4; }
[[ "$(sha256sum "$ARCHIVE" | awk '{print $1}')" == "$EXPECTED_ARCHIVE_SHA" ]] || { echo 'CANDIDATE_SHA=FAIL'; exit 5; }
[[ "$(git -C "$SOURCE" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || { echo 'SOURCE_COMMIT=FAIL'; exit 6; }
[[ -z "$(git -C "$SOURCE" status --porcelain -- installer/phone-rollback-core.sh)" ]] || { echo 'ROLLBACK_CORE_DIRTY=FAIL'; exit 7; }
echo 'VERIFIED_SOURCE_AND_CANDIDATE=PASS'

if [[ -n "${CONTROL_ADB_SERIAL:-}" ]]; then
  SERIAL="$CONTROL_ADB_SERIAL"
else
  mapfile -t DEV < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  (( ${#DEV[@]} == 1 )) || { echo 'ADB_DEVICE_COUNT=FAIL'; exit 8; }
  SERIAL="${DEV[0]}"
fi
adb -s "$SERIAL" get-state | grep -qx device || { echo 'ADB_UNAVAILABLE'; exit 9; }

CORE_SHA="$(sha256sum "$CORE" | awk '{print $1}')"
REMOTE='/data/local/tmp/asfc-rollback-once.sh'
if [[ "$MODE" == '--run' ]]; then
  adb -s "$SERIAL" push "$CORE" "$REMOTE" >/dev/null
fi
cleanup() {
  if [[ "$MODE" == '--run' ]]; then
    adb -s "$SERIAL" shell rm -f "$REMOTE" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

adb -s "$SERIAL" shell \
"run-as com.termux env HOME=/data/data/com.termux/files/home PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin:/system/bin TMPDIR=/data/data/com.termux/files/usr/tmp ASFC_MODE='$MODE' ASFC_BACKUP='$BACKUP_ID' ASFC_CORE_SHA='$CORE_SHA' /data/data/com.termux/files/usr/bin/bash -s" <<'PHONE'
set -Eeuo pipefail
umask 077
PD="$PREFIX/bin/proot-distro"
[[ -x "$PD" ]] || { echo 'PROOT=FAIL'; exit 10; }
for name in asf asf-proxy tailscale-watch; do
  # Exact targets: "asf" could otherwise match the "asf-proxy" prefix.
  tmux has-session -t "=$name" || { echo 'MISSING_TMUX_SESSION'; exit 11; }
done
[[ "$(tmux list-panes -t '=asf' -F '#{pane_id}' | wc -l | tr -d ' ')" == '1' ]] || { echo 'ASF_PANE_COUNT=FAIL'; exit 12; }
CMD="$(tmux display-message -p -t '=asf' '#{pane_start_command}')"
CWD="$(tmux display-message -p -t '=asf' '#{pane_current_path}')"
[[ -n "$CMD" && -d "$CWD" ]] || { echo 'ASF_STARTUP_CAPTURE=FAIL'; exit 13; }
[[ "$CMD" == *while* && "$CMD" == *proot-distro* && "$CMD" == *ArchiSteamFarm* ]] || { echo 'ASF_STARTUP_EXPECTATIONS=FAIL'; exit 14; }
# tmux can reformat the command: do not parse or replay the reported text.
# The captured command is forensic data only; tmux presentation is NOT round-trippable.
# Do not use it to reconstruct the session. A known native boot entrypoint is
# required for recovery.
BOOT="$HOME/.termux/boot/start-asf.sh"
[[ -s "$BOOT" ]] || { echo 'BOOT_SCRIPT_MISSING'; exit 36; }
bash -n "$BOOT" || { echo 'BOOT_SCRIPT_SYNTAX_FAIL'; exit 37; }
for token in tmux proot-distro ArchiSteamFarm; do
  grep -Fq "$token" "$BOOT" || { echo 'BOOT_SCRIPT_CONTRACT_FAIL'; exit 38; }
done
echo 'ASF_SUPERVISOR_BOOT_VERIFIED=PASS'

"$PD" login debian -- env ASFC_BACKUP="$ASFC_BACKUP" /bin/bash -s <<'DEBIAN_PRE'
set -Eeuo pipefail
B="/opt/asf/backups/control-suite/$ASFC_BACKUP"
for f in ArchiSteamFarm PREINSTALL.sha256 ASF.json www/index.html installed-metadata/SHA256SUMS; do
  [[ -s "$B/$f" ]] || { echo 'BACKUP_FILE=FAIL'; exit 16; }
done
for p in PlaytimeGoals AccountManager ControlCenter ControlWeb; do
  [[ -s "$B/plugins/$p/$p.dll" ]] || { echo 'BACKUP_PLUGIN=FAIL'; exit 17; }
done
(cd "$B" && sha256sum --status -c PREINSTALL.sha256)
echo 'BACKUP_INTEGRITY=PASS'
[[ -s /opt/asf/control-suite/installed/SHA256SUMS ]] || exit 18
DEBIAN_PRE

if [[ "$ASFC_MODE" == '--precheck' ]]; then
  echo 'GUARDED_ROLLBACK_PREFLIGHT=PASS'
  exit 0
fi

# Record only a digest and the working directory; never persist the original
# supervisor command since it can contain command-line secrets.
mkdir -p "$HOME/.cache/asf-control-suite"
RECOVERY="$HOME/.cache/asf-control-suite/rollback-command-fingerprint-v3-$ASFC_BACKUP"
[[ ! -e "$RECOVERY" ]] || { echo 'RECOVERY_RECORD_ALREADY_EXISTS'; exit 19; }
{ printf 'cwd_sha256=%s\n' "$(printf %s "$CWD" | sha256sum | cut -d' ' -f1)"; printf 'command_sha256=%s\n' "$(printf %s "$CMD" | sha256sum | cut -d' ' -f1)"; } > "$RECOVERY"
chmod 0600 "$RECOVERY"
echo 'START_COMMAND_FINGERPRINT_SAVED=PASS'

# Verify staged rollback core before disrupting anything.
STAGED="$HOME/.cache/asf-control-suite/rollback-core-$ASFC_BACKUP.sh"
cat "${ASFC_REMOTE_CORE:-/data/local/tmp/asfc-rollback-once.sh}" > "$STAGED"
chmod 0700 "$STAGED"
[[ "$(sha256sum "$STAGED" | awk '{print $1}')" == "$ASFC_CORE_SHA" ]] || { echo 'ROLLBACK_CORE_TRANSFER=FAIL'; exit 20; }
echo 'ROLLBACK_CORE_TRANSFER=PASS'

# The guarded session must have a stable marker, not an exact pane_start_command
# string. tmux can quote/normalize that string and it does not round-trip as a
# shell script (the v1 failure was an example).
BOOT_LOG="$HOME/.cache/asf-control-suite/rollback-asf-only-v3-$ASFC_BACKUP.log"
STATE=0
MUTATION_STARTED=0
GUARD_MARK="asfc-rollback-v3-$ASFC_BACKUP"
guard_active() {
  tmux has-session -t '=asf' 2>/dev/null || return 1
  [[ "$(tmux show-options -t '=asf' -v @asfc_guard 2>/dev/null || true)" == "$GUARD_MARK" ]] || return 1
  [[ "$(tmux display-message -p -t '=asf' '#{pane_dead}')" == 0 ]] || return 1
  [[ "$(tmux list-panes -t '=asf' -F '#{pane_id}' | wc -l | tr -d ' ')" == 1 ]] || return 1
}
# Require a separately reviewed ASF-only launcher at a fixed private path.
# Never execute the multi-service Termux:Boot script as rollback recovery.
# Both executable launcher bytes and the device-specific adapter must be pinned.
asf_only_start_and_wait() {
  local launcher="$HOME/.config/asf/asf-only-launcher.sh"
  local expected="${ASFC_ONLY_LAUNCHER_SHA256:-}"
  local adapter_hash="${ASFC_ONLY_ADAPTER_SHA256:-}"
  [[ -f "$launcher" && ! -L "$launcher" && -s "$launcher" && -r "$launcher" ]] || return 1
  [[ "$expected" =~ ^[0-9a-f]{64}$ && "$adapter_hash" =~ ^[0-9a-f]{64}$ ]] || return 1
  [[ "$(sha256sum "$launcher" | awk '{print $1}')" == "$expected" ]] || return 1
  bash -n "$launcher" >/dev/null 2>&1 || return 1
  # The launcher owns exact session identity and root=200/api=401 checks.
  # Output stays on the device in a private diagnostic file.
  ASFC_ONLY_START_CONFIRMATION=I_APPROVE_ASF_ONLY_START \
    ASFC_ONLY_ADAPTER_SHA256="$adapter_hash" \
    bash "$launcher" --start >"$BOOT_LOG" 2>&1
}
on_guard_error() {
  local status="${1:-$?}"
  trap - ERR HUP INT TERM
  set +e
  if [[ $STATE == 1 && $MUTATION_STARTED == 0 ]]; then
    # Pre-mutation failure: restore original service through native bootstrap.
    if guard_active; then
      tmux kill-session -t '=asf'
    elif tmux has-session -t '=asf' 2>/dev/null; then
      # An unidentified session may own the name: never kill or relabel it.
      echo 'PREMUTATION_UNVERIFIED_SESSION=YES; OPERATOR_REQUIRED=YES'
      exit "$status"
    fi
    if asf_only_start_and_wait; then
      echo 'PREMUTATION_SUPERVISOR_RECOVERED=YES'
    else
      echo 'PREMUTATION_RECOVERY_NEEDS_OPERATOR=YES'
    fi
  elif [[ $MUTATION_STARTED == 1 ]]; then
    echo 'FILES_MAY_BE_CHANGED=YES; DO_NOT_RETRY; PRESERVE_HOLD'
  fi
  exit "$status"
}
# ERR does not handle user interruption or ADB-side termination of the shell.
# Treat these signals as failure and apply the same fail-closed guard rules.
trap 'on_guard_error "$?"' ERR
trap 'on_guard_error 129' HUP
trap 'on_guard_error 130' INT
trap 'on_guard_error 143' TERM

# Hold the session name so another start-asf script cannot recreate it.
# From this point on, any error leaves the hold session in place rather than
# starting a potentially mismatched ASF runtime and plugins.
STATE=1
tmux kill-session -t '=asf'
# Indefinite loop: a long diagnostic pause must not accidentally expire.
tmux new-session -d -s asf -c "$CWD" 'while :; do sleep 3600; done'
tmux set-option -t '=asf' @asfc_guard "$GUARD_MARK"
guard_active || { echo 'HOLD_SESSION_INVALID'; false; }
# Do not inspect pane_start_command as exact text; tmux quotes it differently.
[[ "$(tmux display-message -p -t '=asf' '#{pane_current_command}')" == sleep || "$(tmux display-message -p -t '=asf' '#{pane_current_command}')" == bash ]] || { echo 'HOLD_PANE_UNEXPECTED'; false; }
echo 'SUPERVISOR_HELD=PASS'

# Once the Debian restoration starts, any failure must be handled as potentially
# modified files. Never restart into an unknown runtime/plugin mix.
MUTATION_STARTED=1
# The old ASF child must completely exit and STAY exited before any file swap.
# The watch is performed in one Debian session; we do not signal other services.
"$PD" login debian -- env ASFC_BACKUP="$ASFC_BACKUP" TERMUX_HOME="$HOME" /bin/bash -s <<'DEBIAN_RESTORE'
set -Eeuo pipefail
asf_running() {
  local item arg
  for item in /proc/[0-9]*/cmdline; do
    [[ -r "$item" ]] || continue
    arg=''
    IFS= read -r -d '' arg < "$item" || true
    case "$arg" in
      ArchiSteamFarm|./ArchiSteamFarm|/opt/asf/ArchiSteamFarm) return 0 ;;
    esac
  done
  return 1
}

for i in $(seq 1 60); do
  asf_running || break
  sleep 1
done
if asf_running; then echo 'ASF_STILL_RUNNING=FAIL; NOT MUTATED; HOLD ACTIVE'; exit 23; fi
sleep 3
if asf_running; then echo 'ASF_RESURRECTED=FAIL; NOT MUTATED; HOLD ACTIVE'; exit 24; fi
echo 'ASF_QUIESCENT=PASS'

B="/opt/asf/backups/control-suite/$ASFC_BACKUP"
CORE="$TERMUX_HOME/.cache/asf-control-suite/rollback-core-$ASFC_BACKUP.sh"
# Preserve a marker recording that a file mutation has begun.
printf '%s\n' 'MUTATION_ATTEMPTED' > "$TERMUX_HOME/.cache/asf-control-suite/rollback-phase-$ASFC_BACKUP"
CONTROL_SKIP_PROCESS=1 CONTROL_ROLLBACK_CONFIG=0 bash "$CORE" "$ASFC_BACKUP"

cmp -s "$B/ArchiSteamFarm" /opt/asf/ArchiSteamFarm || { echo 'CORE_RESTORE=FAIL'; exit 25; }
cmp -s "$B/ASF.json" /opt/asf/config/ASF.json || { echo 'CONFIG_RESTORE=FAIL'; exit 26; }
cmp -s "$B/www/index.html" /opt/asf/www/index.html || { echo 'INDEX_RESTORE=FAIL'; exit 27; }
for p in PlaytimeGoals AccountManager ControlCenter ControlWeb; do
  diff -qr "$B/plugins/$p" "/opt/asf/plugins/$p" >/dev/null || { echo 'PLUGIN_RESTORE=FAIL'; exit 28; }
done
diff -qr "$B/installed-metadata" /opt/asf/control-suite/installed >/dev/null || { echo 'META_RESTORE=FAIL'; exit 29; }
echo 'RESTORED_FILES_EXACT=PASS'
DEBIAN_RESTORE

# Safety recheck before unholding: not dependent on tmux command formatting.
guard_active || { echo 'GUARD_WAS_CHANGED=FAIL'; false; }
"$PD" login debian -- /bin/bash -s <<'DEBIAN_IDLE'
set -Eeuo pipefail
for item in /proc/[0-9]*/cmdline; do
  [[ -r "$item" ]] || continue
  arg=''; IFS= read -r -d '' arg < "$item" || true
  case "$arg" in
    ArchiSteamFarm|./ArchiSteamFarm|/opt/asf/ArchiSteamFarm) echo 'UNEXPECTED_ASF_PROCESS=FAIL'; exit 31 ;;
  esac
done
DEBIAN_IDLE

# All restored files are already verified. It is now safe to unhold.
# Never replay pane_start_command or invoke multi-service Termux:Boot.
STATE=2
tmux kill-session -t '=asf'
if ! asf_only_start_and_wait; then
  echo 'ASF_ONLY_RESTART=FAIL; OLD_FILES_VERIFIED; MANUAL_RECOVERY_REQUIRED'
  exit 32
fi
echo 'SUPERVISOR_RESTORED_VIA_ASF_ONLY=PASS'

# Old version has the same base IPC contract; verify its core and control UI.
"$PD" login debian -- /bin/bash -s <<'DEBIAN_HEALTH'
set -Eeuo pipefail
for i in $(seq 1 100); do
  root="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:1242/ 2>/dev/null || true)"
  api="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:1242/Api/ASF 2>/dev/null || true)"
  control="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:1242/Control/ 2>/dev/null || true)"
  if [[ "$root" == 200 && "$api" == 401 && "$control" == 200 ]]; then
    echo 'OLD_RUNTIME_HEALTH=PASS'
    exit 0
  fi
  sleep 1
done
echo 'OLD_RUNTIME_HEALTH=FAIL'; exit 34
DEBIAN_HEALTH

for name in asf asf-proxy tailscale-watch; do
  tmux has-session -t "=$name" || { echo 'SUPERVISOR_MISSING_AFTER=FAIL'; exit 35; }
done
rm -f "$HOME/.cache/asf-control-suite/rollback-phase-$ASFC_BACKUP"
STATE=3
trap - ERR
echo 'GUARDED_ROLLBACK=PASS'
PHONE
