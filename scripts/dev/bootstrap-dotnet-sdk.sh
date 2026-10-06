#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SUITE_ROOT/scripts/build"
MANIFEST="$SUITE_ROOT/release/dotnet-sdk.sha512"

# shellcheck disable=SC1091
. "$BUILD_DIR/pins.sh"

load_release_pins "$SUITE_ROOT/release/pins.env"

RID=""
ARCHIVE=""
INSTALL_DIR=""
VERIFY_ONLY=0
ARCHIVE_IS_USER_SUPPLIED=0

usage() {
    cat >&2 <<USAGE
usage:
  $0 [--rid linux-x64|linux-arm64]
     [--archive /path/to/sdk.tar.gz]
     [--install-dir /path/to/dotnet]
     [--verify-only]

Without --archive, the exact pinned SDK archive is downloaded from
builds.dotnet.microsoft.com.

The archive is SHA-512 verified against release/dotnet-sdk.sha512
before any extraction occurs.
USAGE
}

while (( $# > 0 )); do
    case "$1" in
        --rid)
            [[ $# -ge 2 ]] || {
                usage
                exit 2
            }

            RID="$2"
            shift 2
            ;;

        --archive)
            [[ $# -ge 2 ]] || {
                usage
                exit 2
            }

            ARCHIVE="$2"
            ARCHIVE_IS_USER_SUPPLIED=1
            shift 2
            ;;

        --install-dir)
            [[ $# -ge 2 ]] || {
                usage
                exit 2
            }

            INSTALL_DIR="$2"
            shift 2
            ;;

        --verify-only)
            VERIFY_ONLY=1
            shift
            ;;

        -h|--help)
            usage
            exit 0
            ;;

        *)
            echo "unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$RID" ]]; then
    [[ "$(uname -s)" == "Linux" ]] || {
        echo "automatic RID detection currently supports Linux only" >&2
        exit 3
    }

    case "$(uname -m)" in
        x86_64|amd64)
            RID="linux-x64"
            ;;

        aarch64|arm64)
            RID="linux-arm64"
            ;;

        *)
            echo "unsupported Linux architecture: $(uname -m)" >&2
            exit 3
            ;;
    esac
fi

case "$RID" in
    linux-x64|linux-arm64)
        ;;
    *)
        echo "unsupported SDK RID: $RID" >&2
        exit 4
        ;;
esac

[[ -f "$MANIFEST" ]] || {
    echo "SDK SHA-512 manifest missing: $MANIFEST" >&2
    exit 5
}

MATCH_COUNT="$(
    grep -Ec \
        "^${RID}=[0-9a-f]{128}$" \
        "$MANIFEST" \
        || true
)"

[[ "$MATCH_COUNT" == "1" ]] || {
    echo \
        "expected exactly one valid SHA-512 manifest entry for $RID; found $MATCH_COUNT" \
        >&2
    exit 6
}

EXPECTED_SHA512="$(
    grep -E \
        "^${RID}=[0-9a-f]{128}$" \
        "$MANIFEST" |
        cut -d= -f2
)"

[[ "$EXPECTED_SHA512" =~ ^[0-9a-f]{128}$ ]] || {
    echo "invalid expected SHA-512 for $RID" >&2
    exit 7
}

command -v sha512sum >/dev/null 2>&1 || {
    echo "sha512sum is required" >&2
    exit 8
}

ARCHIVE_NAME="dotnet-sdk-${DOTNET_SDK_VERSION}-${RID}.tar.gz"
DOWNLOAD_URL="https://builds.dotnet.microsoft.com/dotnet/Sdk/${DOTNET_SDK_VERSION}/${ARCHIVE_NAME}"

if [[ -z "$ARCHIVE" ]]; then
    command -v curl >/dev/null 2>&1 || {
        echo "curl is required for explicit SDK bootstrap" >&2
        exit 9
    }

    CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/asf-control-suite/dotnet-downloads"
    ARCHIVE="$CACHE_DIR/$ARCHIVE_NAME"

    mkdir -p "$CACHE_DIR"

    if [[ ! -f "$ARCHIVE" ]]; then
        PARTIAL="${ARCHIVE}.partial.$$"

        cleanup_partial() {
            rm -f "$PARTIAL"
        }

        trap cleanup_partial EXIT

        echo "Downloading official .NET SDK:"
        echo "  $DOWNLOAD_URL"

        curl \
            --proto '=https' \
            --tlsv1.2 \
            --fail \
            --show-error \
            --silent \
            --location \
            --retry 3 \
            --output "$PARTIAL" \
            "$DOWNLOAD_URL" || {
                echo "SDK download failed" >&2
                exit 10
            }

        mv "$PARTIAL" "$ARCHIVE"
        trap - EXIT
    else
        echo "Using cached SDK archive:"
        echo "  $ARCHIVE"
    fi
fi

[[ -f "$ARCHIVE" ]] || {
    echo "SDK archive not found: $ARCHIVE" >&2
    exit 11
}

ACTUAL_SHA512="$(
    sha512sum "$ARCHIVE" |
        awk '{print $1}'
)"

if [[ "$ACTUAL_SHA512" != "$EXPECTED_SHA512" ]]; then
    echo "SDK SHA-512 verification FAILED" >&2
    echo "RID:      $RID" >&2
    echo "Archive:  $ARCHIVE" >&2
    echo "Expected: $EXPECTED_SHA512" >&2
    echo "Actual:   $ACTUAL_SHA512" >&2

    if (( ARCHIVE_IS_USER_SUPPLIED == 0 )); then
        rm -f "$ARCHIVE"
        echo "Removed invalid cached SDK archive." >&2
    fi

    exit 12
fi

echo "SDK SHA-512 verification: PASS"
echo "RID:     $RID"
echo "Archive: $ARCHIVE"

if (( VERIFY_ONLY )); then
    exit 0
fi

command -v tar >/dev/null 2>&1 || {
    echo "tar is required to extract the verified SDK" >&2
    exit 13
}

if [[ -z "$INSTALL_DIR" ]]; then
    INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/asf-control-suite/dotnet-${DOTNET_SDK_VERSION}"
fi

INSTALL_PARENT="$(dirname "$INSTALL_DIR")"
mkdir -p "$INSTALL_PARENT"

if [[ -x "$INSTALL_DIR/dotnet" ]]; then
    EXISTING_SDKS="$(
        "$INSTALL_DIR/dotnet" --list-sdks 2>/dev/null || true
    )"

    if printf '%s\n' "$EXISTING_SDKS" |
        awk -v sdk="$DOTNET_SDK_VERSION" '
            $1 == sdk {
                found = 1
            }

            END {
                exit(found ? 0 : 1)
            }
        '
    then
        echo "Exact SDK is already installed:"
        echo "  $INSTALL_DIR"

        printf '\nUse it for release builds:\n'
        printf '  export CONTROL_DOTNET=%q\n' "$INSTALL_DIR/dotnet"
        exit 0
    fi
fi

STAGE="$(
    mktemp \
        -d \
        "$INSTALL_PARENT/.dotnet-${DOTNET_SDK_VERSION}.stage.XXXXXX"
)" || exit 14

cleanup_stage() {
    rm -rf "$STAGE"
}

trap cleanup_stage EXIT

# Extraction happens only after SHA-512 validation above.
tar \
    -xzf "$ARCHIVE" \
    -C "$STAGE" || {
        echo "verified SDK archive extraction failed" >&2
        exit 15
    }

[[ -x "$STAGE/dotnet" ]] || {
    echo "verified archive did not contain an executable dotnet host" >&2
    exit 16
}

STAGED_SDKS="$(
    "$STAGE/dotnet" --list-sdks 2>/dev/null
)" || {
    echo "extracted dotnet host could not enumerate SDKs" >&2
    exit 17
}

if ! printf '%s\n' "$STAGED_SDKS" |
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
        "verified archive does not contain exact SDK $DOTNET_SDK_VERSION" \
        >&2
    printf '%s\n' "$STAGED_SDKS" >&2
    exit 18
fi

rm -rf "$INSTALL_DIR"

mv \
    "$STAGE" \
    "$INSTALL_DIR" || {
        echo "failed to commit verified SDK installation" >&2
        exit 19
    }

trap - EXIT

echo
echo "Exact .NET SDK installed:"
echo "  $INSTALL_DIR"

printf '\nUse it for release builds:\n'
printf '  export CONTROL_DOTNET=%q\n' "$INSTALL_DIR/dotnet"

printf '\nVerify it with:\n'
printf '  CONTROL_DOTNET=%q %q\n' \
    "$INSTALL_DIR/dotnet" \
    "$SUITE_ROOT/scripts/build/check-dotnet.sh"
