#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/pins.sh"

load_release_pins "$SUITE_ROOT/release/pins.env"

ASF_REPO="${1:-}"
PTG_REPO="${2:-}"
WORKTREE="${3:-$HOME/.cache/asf-control-suite-$ASF_VERSION-v$CONTROL_SUITE_VERSION}"

[[ -n "$ASF_REPO" && -d "$ASF_REPO/.git" ]] || {
    echo "usage: $0 /path/to/ArchiSteamFarm /path/to/PlaytimeGoals [worktree-path]" >&2
    exit 2
}

[[ -n "$PTG_REPO" && -d "$PTG_REPO/.git" ]] || {
    echo "PlaytimeGoals git repo not found: $PTG_REPO" >&2
    exit 3
}

git -C "$ASF_REPO" cat-file -e "${ASF_COMMIT}^{commit}" 2>/dev/null || {
    echo "missing exact ASF commit $ASF_COMMIT" >&2
    exit 4
}

git -C "$PTG_REPO" cat-file -e "${PLAYTIMEGOALS_COMMIT}^{commit}" 2>/dev/null || {
    echo "missing exact PlaytimeGoals commit $PLAYTIMEGOALS_COMMIT" >&2
    exit 5
}

[[ ! -e "$WORKTREE" ]] || {
    echo "worktree exists: $WORKTREE" >&2
    exit 6
}

git -C "$ASF_REPO" worktree add \
    --detach \
    "$WORKTREE" \
    "$ASF_COMMIT"

cleanup() {
    local code=$?

    if (( code )); then
        git -C "$ASF_REPO" worktree remove \
            --force \
            "$WORKTREE" \
            >/dev/null 2>&1 || true
    fi

    exit "$code"
}

trap cleanup ERR

[[ "$(git -C "$WORKTREE" rev-parse HEAD)" == "$ASF_COMMIT" ]] || {
    exit 7
}

git -C "$WORKTREE" submodule update \
    --init \
    --recursive \
    ASF-ui

[[ "$(git -C "$WORKTREE/ASF-ui" rev-parse HEAD)" == "$ASF_UI_COMMIT" ]] || {
    echo "wrong ASF-ui revision" >&2
    exit 8
}

bash "$SCRIPT_DIR/apply-asf-patches.sh" "$WORKTREE"

# Export exact committed PlaytimeGoals source, never dirty working-tree bytes.
git -C "$PTG_REPO" archive \
    "$PLAYTIMEGOALS_COMMIT" \
    PlaytimeGoals |
    tar -xf - -C "$WORKTREE"

for plugin in \
    AccountManager \
    ControlCenter \
    ControlWeb
do
    cp -a \
        "$SUITE_ROOT/src/$plugin" \
        "$WORKTREE/$plugin"
done

python3 \
    "$SUITE_ROOT/scripts/dev/generate-build-info.py" \
    "$SUITE_ROOT/release/pins.env" \
    "$WORKTREE/ControlCenter/Generated/BuildInfo.cs"

[[ -s "$WORKTREE/ControlCenter/Generated/BuildInfo.cs" ]] || {
    echo "generated ControlCenter BuildInfo missing" >&2
    exit 13
}

cat > "$WORKTREE/global.json" <<JSON
{
  "sdk": {
    "version": "$DOTNET_SDK_VERSION",
    "rollForward": "disable",
    "allowPrerelease": false
  }
}
JSON

[[ "$(git -C "$PTG_REPO" rev-parse "$PLAYTIMEGOALS_COMMIT")" == "$PLAYTIMEGOALS_COMMIT" ]] || {
    exit 9
}

[[ -f "$WORKTREE/PlaytimeGoals/PlaytimeGoals.csproj" ]] || {
    echo "PlaytimeGoals export failed" >&2
    exit 10
}

grep -Fq \
    "<Version>$PLAYTIMEGOALS_VERSION</Version>" \
    "$WORKTREE/PlaytimeGoals/PlaytimeGoals.csproj" || {
        echo "unexpected PlaytimeGoals version" >&2
        exit 11
    }

for plugin in \
    AccountManager \
    ControlCenter \
    ControlWeb
do
    grep -Fq \
        "<Version>$CONTROL_MODULE_VERSION</Version>" \
        "$WORKTREE/$plugin/$plugin.csproj" || {
            echo "unexpected $plugin version" >&2
            exit 12
        }
done

git -C "$WORKTREE" diff --check

trap - ERR

printf 'Prepared isolated release worktree: %s\n' "$WORKTREE"
printf 'ASF:           %s\n' "$(git -C "$WORKTREE" rev-parse HEAD)"
printf 'ASF-ui:        %s\n' "$(git -C "$WORKTREE/ASF-ui" rev-parse HEAD)"
printf 'PlaytimeGoals: %s\n' "$PLAYTIMEGOALS_COMMIT"
