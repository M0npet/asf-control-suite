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
OUT_PARENT="${4:-$SUITE_ROOT/artifacts}"

[[ -n "$ASF_REPO" && -n "$PTG_REPO" ]] || {
    echo "usage: $0 /path/to/ArchiSteamFarm /path/to/PlaytimeGoals [worktree] [artifact-dir]" >&2
    exit 2
}

DOTNET_BIN="$(
    "$SCRIPT_DIR/check-dotnet.sh" --print-bin
)" || exit $?

DOTNET_DIR="$(cd "$(dirname "$DOTNET_BIN")" && pwd)"
export PATH="$DOTNET_DIR:$PATH"

python3 "$SUITE_ROOT/tests/static_contracts.py"
python3 "$SUITE_ROOT/tests/pins_single_source.test.py"
bash "$SUITE_ROOT/tests/pins_parser.test.sh"
node "$SUITE_ROOT/tests/control_core.test.js"
bash "$SUITE_ROOT/tests/phone_transaction.test.sh"

if [[ "${CONTROL_RUN_BROWSER_TESTS:-0}" == "1" ]]; then
    python3 "$SUITE_ROOT/tests/ui_integration.py"
fi

bash \
    "$SCRIPT_DIR/prepare-release-worktree.sh" \
    "$ASF_REPO" \
    "$PTG_REPO" \
    "$WORKTREE"

bash \
    "$SCRIPT_DIR/build-release.sh" \
    "$WORKTREE"

bash \
    "$SCRIPT_DIR/package-release.sh" \
    "$WORKTREE" \
    "$OUT_PARENT"

echo "RELEASE READY: $OUT_PARENT/ASF-Control-Suite-v$CONTROL_SUITE_VERSION.zip"
