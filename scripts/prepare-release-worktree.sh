#!/usr/bin/env bash
set -Eeuo pipefail

SUITE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASF_REPO="${1:-}"
PTG_REPO="${2:-}"
WORKTREE="${3:-$HOME/.cache/asf-control-suite-6.3.10.3-v1.0}"
ASF_COMMIT="27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad"
ASF_UI_COMMIT="2b36125533f41e624b2fdcdec44f37ad60c7daaa"
PTG_COMMIT="fa959d3d4ffd09f7fd30e9ee8599aa5004b67033"

[[ -n "$ASF_REPO" && -d "$ASF_REPO/.git" ]] || { echo "usage: $0 /path/to/ArchiSteamFarm /path/to/PlaytimeGoals [worktree-path]" >&2; exit 2; }
[[ -n "$PTG_REPO" && -d "$PTG_REPO/.git" ]] || { echo "PlaytimeGoals git repo not found: $PTG_REPO" >&2; exit 3; }

git -C "$ASF_REPO" cat-file -e "${ASF_COMMIT}^{commit}" 2>/dev/null || { echo "missing exact ASF commit $ASF_COMMIT" >&2; exit 4; }
git -C "$PTG_REPO" cat-file -e "${PTG_COMMIT}^{commit}" 2>/dev/null || { echo "missing exact PlaytimeGoals commit $PTG_COMMIT" >&2; exit 5; }
[[ ! -e "$WORKTREE" ]] || { echo "worktree exists: $WORKTREE" >&2; exit 6; }

git -C "$ASF_REPO" worktree add --detach "$WORKTREE" "$ASF_COMMIT"
cleanup() {
  code=$?
  if (( code )); then
    git -C "$ASF_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  exit "$code"
}
trap cleanup ERR

[[ "$(git -C "$WORKTREE" rev-parse HEAD)" == "$ASF_COMMIT" ]] || exit 7
git -C "$WORKTREE" submodule update --init --recursive ASF-ui
[[ "$(git -C "$WORKTREE/ASF-ui" rev-parse HEAD)" == "$ASF_UI_COMMIT" ]] || { echo "wrong ASF-ui revision" >&2; exit 8; }

# Export exact committed PlaytimeGoals source, never dirty working-tree bytes.
git -C "$PTG_REPO" archive "$PTG_COMMIT" PlaytimeGoals | tar -xf - -C "$WORKTREE"

for plugin in AccountManager ControlCenter ControlWeb; do
  cp -a "$SUITE_ROOT/$plugin" "$WORKTREE/$plugin"
done

cat > "$WORKTREE/global.json" <<'JSON'
{
  "sdk": {
    "version": "10.0.400",
    "rollForward": "disable",
    "allowPrerelease": false
  }
}
JSON

[[ "$(git -C "$PTG_REPO" rev-parse "$PTG_COMMIT")" == "$PTG_COMMIT" ]] || exit 9
[[ -f "$WORKTREE/PlaytimeGoals/PlaytimeGoals.csproj" ]] || { echo "PlaytimeGoals export failed" >&2; exit 10; }
grep -Fq '<Version>0.5.0.0</Version>' "$WORKTREE/PlaytimeGoals/PlaytimeGoals.csproj" || { echo "unexpected PlaytimeGoals version" >&2; exit 11; }
for plugin in AccountManager ControlCenter ControlWeb; do
  grep -Fq '<Version>1.0.0.0</Version>' "$WORKTREE/$plugin/$plugin.csproj" || { echo "unexpected $plugin version" >&2; exit 12; }
done

git -C "$WORKTREE" diff --check
trap - ERR

printf 'Prepared isolated release worktree: %s\n' "$WORKTREE"
printf 'ASF:           %s\n' "$(git -C "$WORKTREE" rev-parse HEAD)"
printf 'ASF-ui:        %s\n' "$(git -C "$WORKTREE/ASF-ui" rev-parse HEAD)"
printf 'PlaytimeGoals: %s\n' "$PTG_COMMIT"
