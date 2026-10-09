#!/usr/bin/env bash
# Read-only on-device preflight for a future synthetic ASF-only rehearsal.
# Does not execute PRoot, candidate, or tmux session creation.
set -u
umask 077
HOME=${HOME:-}
PREFIX=${PREFIX:-}
if [[ -z "$HOME" || -z "$PREFIX" ]]; then
  echo 'TERMUX_ENV=INVALID'
  exit 2
fi
C="$HOME/.cache/asf-control-suite/candidates/asf-only-session.candidate.sh"
A="$HOME/.config/asf/asf-only-session.sh"

state_command() {
  local label=$1 cmd=$2
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '%s=AVAILABLE\n' "$label"
  else
    printf '%s=MISSING\n' "$label"
  fi
}

state_session() {
  local role=$1 name=$2
  if command -v tmux >/dev/null 2>&1 &&
    tmux has-session -t "=$name" >/dev/null 2>&1; then
    printf '%s=PRESENT\n' "$role"
  else
    printf '%s=NOT_CONFIRMED\n' "$role"
  fi
}

echo '=== ASF ISOLATED REHEARSAL PREFLIGHT ==='
state_command TERMUX_BASH bash
state_command TERMUX_TMUX tmux
state_command TERMUX_PROOT_DISTRO proot-distro
state_command TERMUX_MKTEMP mktemp
state_command TERMUX_SHA256SUM sha256sum
state_command TERMUX_TIMEOUT timeout

if command -v tmux >/dev/null 2>&1 && tmux -V >/dev/null 2>&1; then
  echo 'TMUX_CLIENT_BINARY=PASS'
else
  echo 'TMUX_CLIENT_BINARY=NOT_CONFIRMED'
fi

state_session ASF_LIVE_SESSION asf
state_session PROXY_LIVE_SESSION asf-proxy
state_session TAILSCALE_LIVE_SESSION tailscale-watch

if [[ -f "$C" && ! -L "$C" && -s "$C" && -r "$C" ]]; then
  echo 'CANDIDATE=PRIVATE_FILE_PRESENT'
  if [[ "$(stat -c '%a' "$C" 2>/dev/null)" == 600 &&
        "$(stat -c '%u' "$C" 2>/dev/null)" == "$(id -u)" ]]; then
    echo 'CANDIDATE_OWNER_MODE=PASS'
  else
    echo 'CANDIDATE_OWNER_MODE=REVIEW_REQUIRED'
  fi
  if bash -n "$C" >/dev/null 2>&1; then
    echo 'CANDIDATE_SYNTAX=PASS'
  else
    echo 'CANDIDATE_SYNTAX=FAIL'
  fi
else
  echo 'CANDIDATE=MISSING_OR_INVALID'
fi

if [[ ! -e "$A" && ! -L "$A" ]]; then
  echo 'ACTIVE_ADAPTER=NOT_INSTALLED'
else
  echo 'ACTIVE_ADAPTER=EXISTS_REVIEW_REQUIRED'
fi

# Do not print sizes or device/storage paths. No files are created here.
if command -v df >/dev/null 2>&1; then
  free_kib=$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2 {print $4}')
  if [[ "$free_kib" =~ ^[0-9]+$ ]] && (( free_kib >= 65536 )); then
    echo 'TEMP_WORKSPACE_SPACE=SUFFICIENT_64M'
  else
    echo 'TEMP_WORKSPACE_SPACE=UNKNOWN_OR_LOW'
  fi
else
  echo 'TEMP_WORKSPACE_SPACE=UNKNOWN_OR_LOW'
fi

echo 'TEST_TMUX_SOCKET=NOT_CREATED'
echo 'PROOT_EXECUTION=NOT_ATTEMPTED'
echo 'CANDIDATE_EXECUTION=NOT_ATTEMPTED'
echo 'PREFLIGHT_READ_ONLY=PASS'
