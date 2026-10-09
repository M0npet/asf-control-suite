#!/usr/bin/env bash
# Termux-local, experimental ASF-only launcher. Never invokes Termux:Boot.
# DO NOT run --start on Mi Max 2 until its ASF adapter has been audited.
set -Eeuo pipefail
umask 077
MODE="${1:---audit}"
case "$MODE" in --audit|--start) ;; *) echo 'USAGE=asf-only-launcher.sh [--audit|--start]' >&2; exit 2;; esac

if [[ "$MODE" == --start && "${ASFC_ONLY_START_CONFIRMATION:-}" != 'I_APPROVE_ASF_ONLY_START' ]]; then
  echo 'ASF_ONLY_START_CONFIRMATION_REQUIRED; NOT STARTED' >&2
  exit 2
fi

: "${HOME:?HOME is required}"
ADAPTER="$HOME/.config/asf/asf-only-session.sh"
LOCK="$HOME/.cache/asf-control-suite/asf-only-start.lock"
EXPECTED_SHA="${ASFC_ONLY_ADAPTER_SHA256:-}"

has() { tmux has-session -t "=$1" 2>/dev/null; }
sid() {
  # display-message -t accepts a target-pane; a session may exist without a
  # resolvable pane. list-sessions is the authoritative session inventory.
  local wanted="$1" listing row name found='' candidate
  listing="$(tmux list-sessions -F '#{session_name}|#{session_id}' 2>/dev/null)" || return 1
  while IFS= read -r row; do
    [[ "$row" == *'|'* ]] || continue
    name="${row%%|*}"
    candidate="${row#*|}"
    if [[ "$name" == "$wanted" ]]; then
      [[ -z "$found" && "$candidate" =~ ^\$[0-9]+$ ]] || return 1
      found="$candidate"
    fi
  done <<< "$listing"
  [[ -n "$found" ]] || return 1
  printf '%s' "$found"
}

# Adapter is deliberately not included in the repository: its exact launch
# block must be derived from and audited against THIS phone's Termux:Boot.
adapter_ready() {
  [[ -f "$ADAPTER" && ! -L "$ADAPTER" && -s "$ADAPTER" && -r "$ADAPTER" ]] || return 1
  [[ "$EXPECTED_SHA" =~ ^[0-9a-f]{64}$ ]] || return 1
  [[ "$(sha256sum "$ADAPTER" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || return 1
  bash -n "$ADAPTER" >/dev/null 2>&1 || return 1
}

if [[ "$MODE" == --audit ]]; then
  printf 'ASF_SESSION=%s\n' "$(has asf && echo PRESENT || echo MISSING)"
  printf 'PROXY_SESSION=%s\n' "$(has asf-proxy && echo PRESENT || echo MISSING)"
  printf 'TAILSCALE_SESSION=%s\n' "$(has tailscale-watch && echo PRESENT || echo MISSING)"
  if adapter_ready; then
    echo 'ASF_ONLY_ADAPTER=PINNED_AND_SYNTAX_OK'
  else
    echo 'ASF_ONLY_ADAPTER=NOT_READY'
  fi
  echo 'ASF_ONLY_AUDIT_READ_ONLY=PASS'
  exit 0
fi

command -v tmux >/dev/null || { echo 'TMUX_MISSING' >&2; exit 3; }
command -v curl >/dev/null || { echo 'CURL_MISSING' >&2; exit 3; }
RETRIES="${ASFC_ONLY_HEALTH_RETRIES:-60}"
[[ "$RETRIES" =~ ^[1-9][0-9]*$ && ${#RETRIES} -le 3 ]] && (( RETRIES <= 120 )) || {
  echo 'INVALID_HEALTH_RETRIES' >&2; exit 20;
}
adapter_ready || { echo 'ASF_ONLY_ADAPTER_NOT_APPROVED; NOT STARTED' >&2; exit 10; }
has asf && { echo 'ASF_SESSION_ALREADY_EXISTS; NOT STARTED' >&2; exit 11; }
for name in asf-proxy tailscale-watch; do
  has "$name" || { echo 'DEPENDENCY_SESSION_MISSING; NOT STARTED' >&2; exit 12; }
done
PROXY_ID="$(sid asf-proxy)" || { echo 'DEPENDENCY_ID_MISSING; NOT STARTED' >&2; exit 13; }
TAILSCALE_ID="$(sid tailscale-watch)" || { echo 'DEPENDENCY_ID_MISSING; NOT STARTED' >&2; exit 13; }
[[ -n "$PROXY_ID" && -n "$TAILSCALE_ID" ]] || { echo 'DEPENDENCY_ID_MISSING; NOT STARTED' >&2; exit 13; }

# Validate health-check controls BEFORE executing the trusted adapter.
# Malformed retry settings must not create an ASF session.
# HTTP 000 alone is ambiguous: curl also reports it for a listening but
# unresponsive server. Only exit 7 (TCP connection failed) plus HTTP 000
# permits an ASF-only start. All timeouts and other errors fail closed.
# Bypass inherited proxies when probing 127.0.0.1.
if code="$(curl --noproxy '*' -sS --connect-timeout 1 --max-time 2 -o /dev/null -w '%{http_code}' http://127.0.0.1:1242/ 2>/dev/null)"; then
  echo 'ORPHAN_ASF_HTTP_LISTENER; NOT STARTED' >&2
  exit 14
else
  probe_rc=$?
  [[ "$probe_rc" == 7 && "$code" == 000 ]] || {
    echo 'ASF_IPC_PROBE_INDETERMINATE; NOT STARTED' >&2; exit 24;
  }
fi

mkdir -p "$(dirname "$LOCK")"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo 'ASF_ONLY_LAUNCH_LOCKED; NOT STARTED' >&2
  exit 15
fi
STAGED=''
cleanup() {
  [[ -z "$STAGED" ]] || rm -f -- "$STAGED"
  rmdir "$LOCK" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
has asf && { echo 'ASF_SESSION_APPEARED; NOT STARTED' >&2; exit 16; }

# Snapshot the adapter after obtaining the lock and hash the *bytes that
# will be executed*, preventing check/use races during a local file change.
STAGED="$(mktemp "$HOME/.cache/asf-control-suite/asf-only-pinned.XXXXXXXX")"
cat -- "$ADAPTER" > "$STAGED"
[[ "$(sha256sum "$STAGED" | awk '{print $1}')" == "$EXPECTED_SHA" ]] &&
  bash -n "$STAGED" >/dev/null 2>&1 || {
    echo 'ASF_ONLY_ADAPTER_CHANGED; NOT STARTED' >&2; exit 23;
  }
# The pinned local adapter must create only the exact named 'asf' tmux
# session. It MUST NOT call Termux:Boot or manipulate other sessions.
# No eval and no pane_start_command round-trip are involved.
if ! bash "$STAGED" >/dev/null 2>&1; then
  echo 'ASF_ONLY_ADAPTER_FAILED; OPERATOR_REVIEW_REQUIRED' >&2
  exit 17
fi
has asf || { echo 'ASF_ONLY_SESSION_NOT_CREATED' >&2; exit 18; }
# Observe the exact new session identity. A mere 'has-session' is insufficient:
# a rapidly crashing/replaced supervisor must never pass the health gate.
ASF_ID="$(sid asf)" || { echo 'ASF_ONLY_SESSION_ID_UNAVAILABLE' >&2; exit 18; }
check_asf_identity() {
  has asf && [[ "$(sid asf)" == "$ASF_ID" ]]
}
check_dependencies() {
  has asf-proxy && has tailscale-watch &&
    [[ "$(sid asf-proxy)" == "$PROXY_ID" ]] &&
    [[ "$(sid tailscale-watch)" == "$TAILSCALE_ID" ]]
}
check_dependencies || { echo 'AUXILIARY_SESSION_CHANGED; OPERATOR_REVIEW_REQUIRED' >&2; exit 19; }

for (( i=0; i<RETRIES; i++ )); do
  check_dependencies || { echo 'AUXILIARY_SESSION_CHANGED; OPERATOR_REVIEW_REQUIRED' >&2; exit 19; }
  has asf || { echo 'ASF_ONLY_SESSION_LOST; OPERATOR_REVIEW_REQUIRED' >&2; exit 21; }
  check_asf_identity || { echo 'ASF_ONLY_SESSION_REPLACED; OPERATOR_REVIEW_REQUIRED' >&2; exit 25; }
  root="$(curl --noproxy '*' -sS --max-time 3 -o /dev/null -w '%{http_code}' http://127.0.0.1:1242/ 2>/dev/null || true)"
  api="$(curl --noproxy '*' -sS --max-time 3 -o /dev/null -w '%{http_code}' http://127.0.0.1:1242/Api/ASF 2>/dev/null || true)"
  if [[ "$root" == 200 && "$api" == 401 ]]; then
    # A dependency could restart between the precheck and the HTTP response.
    check_dependencies || { echo 'AUXILIARY_SESSION_CHANGED; OPERATOR_REVIEW_REQUIRED' >&2; exit 19; }
    has asf || { echo 'ASF_ONLY_SESSION_LOST; OPERATOR_REVIEW_REQUIRED' >&2; exit 21; }
    check_asf_identity || { echo 'ASF_ONLY_SESSION_REPLACED; OPERATOR_REVIEW_REQUIRED' >&2; exit 25; }
    echo 'ASF_ONLY_LAUNCH=PASS'
    exit 0
  fi
  sleep 1
done
echo 'ASF_ONLY_HEALTH_TIMEOUT; OPERATOR_REVIEW_REQUIRED' >&2
exit 22
