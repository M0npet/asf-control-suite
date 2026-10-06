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

ensure_dotnet() {
    local sdk="$DOTNET_SDK_VERSION"

    if \
        command -v dotnet >/dev/null 2>&1 && \
        dotnet --list-sdks 2>/dev/null |
            grep -Eq "^${sdk//./\\.}[[:space:]]"
    then
        return 0
    fi

    command -v curl >/dev/null 2>&1 || {
        echo "curl is required to bootstrap .NET SDK $sdk" >&2
        exit 3
    }

    local cache="${XDG_CACHE_HOME:-$HOME/.cache}/asf-control-suite"
    local install_dir="$cache/dotnet-$sdk"
    local installer="$cache/dotnet-install.sh"

    mkdir -p "$cache"

    if \
        [[ ! -x "$install_dir/dotnet" ]] || \
        [[ "$("$install_dir/dotnet" --version 2>/dev/null || true)" != "$sdk" ]]
    then
        curl \
            --fail \
            --show-error \
            --silent \
            --location \
            https://dot.net/v1/dotnet-install.sh \
            -o "$installer"

        chmod 0700 "$installer"
        rm -rf "$install_dir"

        bash "$installer" \
            --version "$sdk" \
            --install-dir "$install_dir" \
            --no-path
    fi

    [[ "$("$install_dir/dotnet" --version)" == "$sdk" ]] || {
        echo "failed to bootstrap exact .NET SDK $sdk" >&2
        exit 4
    }

    export DOTNET_ROOT="$install_dir"
    export PATH="$install_dir:$PATH"
}

[[ -n "$ASF_REPO" && -n "$PTG_REPO" ]] || {
    echo "usage: $0 /path/to/ArchiSteamFarm /path/to/PlaytimeGoals [worktree] [artifact-dir]" >&2
    exit 2
}

ensure_dotnet

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

CONTROL_SUITE_SOURCE="$SUITE_ROOT" \
    bash \
    "$SCRIPT_DIR/package-release.sh" \
    "$WORKTREE" \
    "$OUT_PARENT"

echo "RELEASE READY: $OUT_PARENT/asf-control-suite-v1.0-dist.tar.gz"
