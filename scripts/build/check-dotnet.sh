#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/pins.sh"

load_release_pins "$SUITE_ROOT/release/pins.env"

MODE="${1:-}"

case "$MODE" in
    ""|--print-bin)
        ;;
    *)
        echo "usage: $0 [--print-bin]" >&2
        exit 2
        ;;
esac

DOTNET_BIN="${CONTROL_DOTNET:-}"

if [[ -z "$DOTNET_BIN" ]]; then
    DOTNET_BIN="$(command -v dotnet 2>/dev/null || true)"
fi

if [[ -z "$DOTNET_BIN" ]]; then
    echo \
        "exact .NET SDK $DOTNET_SDK_VERSION is required, but dotnet is not available" \
        >&2
    echo \
        "run scripts/dev/bootstrap-dotnet-sdk.sh, then set CONTROL_DOTNET to the installed dotnet binary" \
        >&2
    exit 3
fi

if [[ "$DOTNET_BIN" != */* ]]; then
    DOTNET_BIN="$(command -v "$DOTNET_BIN" 2>/dev/null || true)"
fi

if [[ -z "$DOTNET_BIN" || ! -x "$DOTNET_BIN" ]]; then
    echo "dotnet executable is not usable: ${CONTROL_DOTNET:-<PATH>}" >&2
    exit 4
fi

SDK_LIST="$("$DOTNET_BIN" --list-sdks 2>/dev/null)" || {
    echo "failed to query installed .NET SDKs: $DOTNET_BIN" >&2
    exit 5
}

if ! printf '%s\n' "$SDK_LIST" |
    awk -v sdk="$DOTNET_SDK_VERSION" '
        $1 == sdk {
            found = 1
        }

        END {
            exit(found ? 0 : 1)
        }
    '
then
    echo \
        "exact .NET SDK $DOTNET_SDK_VERSION is not installed for $DOTNET_BIN" \
        >&2

    if [[ -n "$SDK_LIST" ]]; then
        echo "available SDKs:" >&2
        printf '%s\n' "$SDK_LIST" >&2
    else
        echo "available SDKs: none" >&2
    fi

    echo \
        "release build aborted; SDK roll-forward is not permitted" \
        >&2
    exit 6
fi

if [[ "$MODE" == "--print-bin" ]]; then
    printf '%s\n' "$DOTNET_BIN"
else
    printf \
        'Exact .NET SDK %s available via %s\n' \
        "$DOTNET_SDK_VERSION" \
        "$DOTNET_BIN"
fi
