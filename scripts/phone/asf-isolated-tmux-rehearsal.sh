#!/usr/bin/env bash
# Termux-local live-tmux rehearsal, using an independent private socket.
# Runs ONLY the generated harmless worker; never executes PRoot, ASF or adapter.
set -Eeuo pipefail
umask 077

[[ "${1:---audit}" == '--run-synthetic' ]] || {
  echo 'USAGE=--run-synthetic; NOT STARTED'
  exit 2
}

: "${HOME:?}"
: "${PREFIX:?}"
: "${TMPDIR:?}"
unset TMUX

C="$HOME/.cache/asf-control-suite/candidates/asf-only-session.candidate.sh"
A="$HOME/.config/asf/asf-only-session.sh"

fail() { printf '%s\n' "$1"; exit "$2"; }

[[ -f "$C" && -s "$C" && -r "$C" && ! -L "$C" ]] || fail 'CANDIDATE_PRECHECK=FAIL' 10
[[ "$(stat -c '%a' "$C" 2>/dev/null)" == 600 ]] || fail 'CANDIDATE_MODE=FAIL' 11
[[ "$(stat -c '%u' "$C" 2>/dev/null)" == "$(id -u)" ]] || fail 'CANDIDATE_OWNER=FAIL' 12
bash -n "$C" >/dev/null 2>&1 || fail 'CANDIDATE_SYNTAX=FAIL' 13
[[ ! -e "$A" && ! -L "$A" ]] || fail 'ACTIVE_ADAPTER=EXISTS; NOT STARTED' 14

for command_name in tmux timeout mktemp stat id; do
  command -v "$command_name" >/dev/null 2>&1 || fail 'TEST_PREREQUISITE=MISSING' 15
done
[[ -d "$TMPDIR" && -w "$TMPDIR" && ! -L "$TMPDIR" ]] || fail 'PRIVATE_TMPDIR=INVALID' 16
BASH_BIN="$(command -v bash)"
[[ -x "$BASH_BIN" ]] || fail 'BASH_BINARY=INVALID' 17

# Read only: snapshot exact session IDs from the DEFAULT tmux server.
for name in asf asf-proxy tailscale-watch; do
  timeout 5 tmux has-session -t "=$name" >/dev/null 2>&1 || fail 'LIVE_SESSIONS=NOT_READY' 18
done
id_asf="$(timeout 5 tmux display-message -p -t '=asf' '#{session_id}' 2>/dev/null)" || fail 'LIVE_ID=UNAVAILABLE' 19
id_proxy="$(timeout 5 tmux display-message -p -t '=asf-proxy' '#{session_id}' 2>/dev/null)" || fail 'LIVE_ID=UNAVAILABLE' 19
id_tail="$(timeout 5 tmux display-message -p -t '=tailscale-watch' '#{session_id}' 2>/dev/null)" || fail 'LIVE_ID=UNAVAILABLE' 19
[[ -n "$id_asf" && -n "$id_proxy" && -n "$id_tail" ]] || fail 'LIVE_ID=UNAVAILABLE' 19

WORKDIR=''
SOCKET=''
cleanup() {
  if [[ -n "$SOCKET" ]]; then
    timeout 5 tmux -S "$SOCKET" kill-server >/dev/null 2>&1 || true
  fi
  if [[ -n "$WORKDIR" && -d "$WORKDIR" ]]; then
    rm -f -- "$WORKDIR/worker.sh" "$WORKDIR/started" "$WORKDIR/socket"
    rmdir -- "$WORKDIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

WORKDIR="$(mktemp -d "$TMPDIR/asfc-isolated.XXXXXXXX")" || fail 'SANDBOX_CREATE=FAIL' 20
chmod 700 "$WORKDIR"
SOCKET="$WORKDIR/socket"
WORKER="$WORKDIR/worker.sh"

# No PRoot, no ASF executable, no candidate source. Generated constants only.
cat > "$WORKER" <<'WORKER_SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
printf 'OK\n' > "$DIR/started"
while :; do sleep 1; done
WORKER_SCRIPT
chmod 700 "$WORKER"

if timeout 3 tmux -S "$SOCKET" has-session >/dev/null 2>&1; then
  fail 'SOCKET_ALREADY_ACTIVE; NOT STARTED' 21
fi

printf -v cmd 'exec %q %q' "$BASH_BIN" "$WORKER"
timeout 8 tmux -S "$SOCKET" -f /dev/null new-session -d -s asfc-isolated "$cmd" \
  >/dev/null 2>&1 || fail 'ISOLATED_TMUX_CREATE=FAIL' 22

echo 'ISOLATED_TMUX_CREATE=PASS'

worker_ready=NO
for ((i=0; i<30; i++)); do
  if [[ -f "$WORKDIR/started" ]] &&
     timeout 5 tmux -S "$SOCKET" has-session -t '=asfc-isolated' >/dev/null 2>&1; then
    worker_ready=YES
    break
  fi
  sleep 0.2
done
[[ "$worker_ready" == YES ]] || fail 'ISOLATED_WORKER=FAIL' 23
echo 'ISOLATED_WORKER=PASS'

# Recheck actual live server; compare identities in-memory only.
new_asf="$(timeout 5 tmux display-message -p -t '=asf' '#{session_id}' 2>/dev/null)" || fail 'LIVE_SESSION_CHECK=FAIL' 24
new_proxy="$(timeout 5 tmux display-message -p -t '=asf-proxy' '#{session_id}' 2>/dev/null)" || fail 'LIVE_SESSION_CHECK=FAIL' 24
new_tail="$(timeout 5 tmux display-message -p -t '=tailscale-watch' '#{session_id}' 2>/dev/null)" || fail 'LIVE_SESSION_CHECK=FAIL' 24
[[ "$id_asf" == "$new_asf" && "$id_proxy" == "$new_proxy" && "$id_tail" == "$new_tail" ]] \
  || fail 'LIVE_SESSIONS=CHANGED' 25

echo 'LIVE_SESSIONS=UNCHANGED'
echo 'PROOT_EXECUTION=NOT_ATTEMPTED'
echo 'CANDIDATE_EXECUTION=NOT_ATTEMPTED'

# Shut down exclusively the private server; cleanup trap is a fallback.
timeout 5 tmux -S "$SOCKET" kill-server >/dev/null 2>&1 || fail 'ISOLATED_TMUX_CLEANUP=FAIL' 26
if timeout 3 tmux -S "$SOCKET" has-session >/dev/null 2>&1; then
  fail 'ISOLATED_TMUX_CLEANUP=FAIL' 26
fi
echo 'ISOLATED_TMUX_CLEANUP=PASS'
echo 'SYNTHETIC_REHEARSAL=PASS'
