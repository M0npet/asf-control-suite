#!/usr/bin/env bash
# Experimental on-device *candidate* preparer: does NOT launch or install ASF.
# Every diagnostic is an enumerated label; no contents or paths are printed.
set -Eeuo pipefail
umask 077
MODE="${1:---audit}"
case "$MODE" in --audit|--prepare) ;; *) echo 'USAGE=--audit|--prepare'; exit 2;; esac
BOOT="${ASFC_BOOT_FILE:-$HOME/.termux/boot/start-asf.sh}"
OUT="${ASFC_CANDIDATE_PATH:-$HOME/.cache/asf-control-suite/candidates/asf-only-session.candidate.sh}"
[[ -f "$BOOT" && -r "$BOOT" && ! -L "$BOOT" ]] || { echo 'BOOT_FILE=INVALID'; exit 3; }
bash -n "$BOOT" >/dev/null 2>&1 || { echo 'BOOT_SYNTAX=FAIL'; exit 4; }
mapfile -t L < "$BOOT"
(( ${#L[@]} >= 36 )) || { echo 'BOOT_LAYOUT=INVALID'; exit 5; }
# This is explicitly anchored to the known, audited Mi Max 2 stanza.
# Refuse if the layout has changed: never search blindly for commands.
[[ "${L[22]}" == *'tmux has-session'* && "${L[25]}" == *'tmux new-session'* ]] || {
  echo 'ASF_STANZA_LAYOUT=CHANGED'; exit 6;
}
[[ "${L[27]}" == *'proot-distro'* && "${L[29]}" == *'ArchiSteamFarm'* ]] || {
  echo 'ASF_LAUNCH_SHAPE=CHANGED'; exit 7;
}
# Find the shortest Bash-complete fragment starting at original line 26.
# Never include the conditional's log branch or auxiliary services.
FRAGMENT=''
END_LINE=0
for ((n=26; n<=34; n++)); do
  FRAGMENT+="${L[n-1]}"$'\n'
  [[ "$FRAGMENT" == *'proot-distro'* && "$FRAGMENT" == *'ArchiSteamFarm'* && "$FRAGMENT" == *'sleep'* ]] || continue
  if bash -n >/dev/null 2>&1 <<< "$FRAGMENT"; then
    END_LINE=$n
    break
  fi
done
(( END_LINE > 0 )) || { echo 'ASF_FRAGMENT=INCOMPLETE'; exit 8; }
# Narrow static gates. A trusted operator must still inspect the candidate
# privately because text matches are not a substitute for Bash AST review.
if [[ "$FRAGMENT" == *'asf-proxy'* || "$FRAGMENT" == *'tailscale-watch'* ||
      "$FRAGMENT" == *'kill-session'* || "$FRAGMENT" == *'kill-server'* ||
      "$FRAGMENT" == *'send-keys'* || "$FRAGMENT" == *'start-asf.sh'* ||
      "$FRAGMENT" == *'eval '* || "$FRAGMENT" == *'${!'* ||
      "$FRAGMENT" == *'$('* || "$FRAGMENT" == *'`'* ]]; then
  echo 'ASF_FRAGMENT=UNSAFE_TOKEN'; exit 9
fi
# Reject suspiciously duplicated tmux operations in the ASF fragment.
# grep -c counts *lines*, so two operations on one line previously looked safe.
count=$(grep -o 'tmux new-session' <<< "$FRAGMENT" | wc -l | tr -d ' ')
[[ "$count" == 1 ]] || { echo 'ASF_FRAGMENT=MULTIPLE_TMUX_OPS'; exit 10; }
# Require a literal session identity. Indirection needs manual review.
if [[ "$FRAGMENT" != *' -s asf '* && "$FRAGMENT" != *' -s "asf" '* &&
      "$FRAGMENT" != *" -s 'asf' "* ]]; then
  echo 'ASF_SESSION_NAME=NOT_LITERAL'; exit 11
fi
# Quoting consistency is verified on the completed candidate, not merely lines.
CANDIDATE=$'#!/usr/bin/env bash\nset -Eeuo pipefail\n'"$FRAGMENT"
bash -n >/dev/null 2>&1 <<< "$CANDIDATE" || { echo 'CANDIDATE_SYNTAX=FAIL'; exit 12; }
echo 'ASF_LAUNCH_FRAGMENT=VALIDATED_STATICALLY'
echo "ASF_FRAGMENT_END_LINE=$END_LINE"
if [[ "$MODE" == '--audit' ]]; then
  echo 'CANDIDATE_FILE=NOT_WRITTEN'
  echo 'ADAPTER_NOT_EXECUTED=PASS'
  exit 0
fi
# Candidate path intentionally differs from the executable adapter path.
# Only a second, separately authorized deployment can install/execute it.
# Compare canonical paths, not only literal strings: a different spelling
# (../ components or a symlinked parent) could otherwise write the active
# executable adapter without independent approval.
command -v realpath >/dev/null 2>&1 || { echo 'REALPATH=MISSING'; exit 19; }
OUT_CANONICAL="$(realpath -m -- "$OUT")" || { echo 'CANDIDATE_PATH=INVALID'; exit 19; }
ACTIVE_CANONICAL="$(realpath -m -- "$HOME/.config/asf/asf-only-session.sh")" ||
  { echo 'ACTIVE_ADAPTER_PATH=INVALID'; exit 19; }
[[ "$OUT_CANONICAL" != "$ACTIVE_CANONICAL" ]] || {
  echo 'CANDIDATE_PATH=EXECUTABLE_PATH_REFUSED'; exit 13
}
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'CANDIDATE_ALREADY_EXISTS'; exit 14; }
DIR="$(dirname -- "$OUT")"
mkdir -p -m 700 -- "$DIR"
[[ -d "$DIR" && ! -L "$DIR" ]] || { echo 'CANDIDATE_DIR=INVALID'; exit 15; }
STAGED="$(mktemp "$DIR/.asfc-candidate.XXXXXXXX")"
cleanup() { [[ -z "${STAGED:-}" ]] || rm -f -- "$STAGED"; }
trap cleanup EXIT
printf '%s' "$CANDIDATE" > "$STAGED"
chmod 600 "$STAGED"
bash -n "$STAGED" >/dev/null 2>&1 || { echo 'CANDIDATE_SYNTAX=FAIL'; exit 16; }
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'CANDIDATE_ALREADY_EXISTS'; exit 14; }
# Atomically reserve the destination. 'mv -n' can silently skip an
# existing target and still return success, yielding a false PASS on races.
# Staged and destination are in the same private directory, so a hard link
# is an exclusive, no-overwrite commit; cleanup removes the temporary name.
if ! ln -- "$STAGED" "$OUT" 2>/dev/null; then
  echo 'CANDIDATE_COMMIT_REFUSED'; exit 18
fi
rm -f -- "$STAGED"
STAGED=''
[[ -s "$OUT" && ! -L "$OUT" ]] || { echo 'CANDIDATE_INSTALL=FAIL'; exit 17; }
echo 'CANDIDATE_FILE=PRIVATE_REVIEW_ONLY'
echo 'ADAPTER_NOT_EXECUTED=PASS'
