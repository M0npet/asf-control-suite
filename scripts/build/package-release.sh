#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/pins.sh"

load_release_pins \
    "$SUITE_ROOT/release/pins.env"

ASF_ROOT="${1:-$(pwd)}"
OUT_PARENT="${2:-$SUITE_ROOT/artifacts}"

cd "$ASF_ROOT"

[[ "$(git rev-parse HEAD)" == "$ASF_COMMIT" ]] || {
    echo "wrong ASF HEAD" >&2
    exit 2
}

[[ \
    "$(git -C ASF-ui rev-parse HEAD)" \
    == "$ASF_UI_COMMIT" \
]] || {
    echo "wrong ASF-ui HEAD" >&2
    exit 3
}

ASF_RUNTIME="out/control-suite-linux-arm64/ArchiSteamFarm"

[[ -s "$ASF_RUNTIME" && -x "$ASF_RUNTIME" ]] || {
    echo "missing patched ASF runtime: $ASF_RUNTIME" >&2
    exit 4
}

for plugin in \
    PlaytimeGoals \
    AccountManager \
    ControlCenter \
    ControlWeb
do
    DLL="$plugin/bin/Release/net10.0/$plugin.dll"

    [[ -s "$DLL" ]] || {
        echo "missing release DLL: $DLL" >&2
        exit 4
    }
done

for asset in \
    index.html \
    i18n.js \
    core.js \
    qrcode.min.js \
    qrcode.LICENSE.txt \
    app.js \
    app.css
do
    [[ \
        -s \
        "ControlWeb/bin/Release/net10.0/www/$asset" \
    ]] || {
        echo \
            "missing ControlWeb release asset: $asset" \
            >&2
        exit 5
    }
done

mkdir -p "$OUT_PARENT"

STAGE_ROOT="$(
    mktemp \
        -d \
        "$OUT_PARENT/.native-stage.XXXXXX"
)" || exit 6

cleanup_stage() {
    rm -rf "$STAGE_ROOT"
}

trap cleanup_stage EXIT

mkdir -p \
    "$STAGE_ROOT/PlaytimeGoals" \
    "$STAGE_ROOT/AccountManager" \
    "$STAGE_ROOT/ControlCenter" \
    "$STAGE_ROOT/ControlWeb/www"

cp \
    PlaytimeGoals/bin/Release/net10.0/PlaytimeGoals.dll \
    "$STAGE_ROOT/PlaytimeGoals/PlaytimeGoals.dll"

cp \
    AccountManager/bin/Release/net10.0/AccountManager.dll \
    "$STAGE_ROOT/AccountManager/AccountManager.dll"

cp \
    ControlCenter/bin/Release/net10.0/ControlCenter.dll \
    "$STAGE_ROOT/ControlCenter/ControlCenter.dll"

cp \
    ControlWeb/bin/Release/net10.0/ControlWeb.dll \
    "$STAGE_ROOT/ControlWeb/ControlWeb.dll"

cp -a \
    ControlWeb/bin/Release/net10.0/www/. \
    "$STAGE_ROOT/ControlWeb/www/"

if find "$STAGE_ROOT" \
    -type l \
    -print \
    -quit |
    grep -q .
then
    echo \
        "symlinks are forbidden in native plugin stage" \
        >&2
    exit 7
fi

EXPECTED_STAGE_FILES=(
    "AccountManager/AccountManager.dll"
    "ControlCenter/ControlCenter.dll"
    "ControlWeb/ControlWeb.dll"
    "ControlWeb/www/app.css"
    "ControlWeb/www/app.js"
    "ControlWeb/www/core.js"
    "ControlWeb/www/i18n.js"
    "ControlWeb/www/index.html"
    "ControlWeb/www/qrcode.LICENSE.txt"
    "ControlWeb/www/qrcode.min.js"
    "PlaytimeGoals/PlaytimeGoals.dll"
)

mapfile -t ACTUAL_STAGE_FILES < <(
    cd "$STAGE_ROOT"

    find \
        . \
        -type f \
        -printf '%P\n' |
        sort
)

mapfile -t EXPECTED_SORTED < <(
    printf '%s\n' \
        "${EXPECTED_STAGE_FILES[@]}" |
        sort
)

if [[ \
    "$(printf '%s\n' "${ACTUAL_STAGE_FILES[@]}")" \
    != \
    "$(printf '%s\n' "${EXPECTED_SORTED[@]}")" \
]]
then
    echo \
        "canonical native stage does not match expected layout" \
        >&2

    echo "Expected:" >&2
    printf '  %s\n' \
        "${EXPECTED_SORTED[@]}" \
        >&2

    echo "Actual:" >&2
    printf '  %s\n' \
        "${ACTUAL_STAGE_FILES[@]}" \
        >&2

    exit 8
fi

BUNDLE_ZIP="$OUT_PARENT/ASF-Control-Suite-v$CONTROL_SUITE_VERSION.zip"
ACCOUNT_ZIP="$OUT_PARENT/AccountManager-v$CONTROL_SUITE_VERSION.zip"
CENTER_ZIP="$OUT_PARENT/ControlCenter-v$CONTROL_SUITE_VERSION.zip"
WEB_ZIP="$OUT_PARENT/ControlWeb-v$CONTROL_SUITE_VERSION.zip"
PTG_ZIP="$OUT_PARENT/PlaytimeGoals-v${PLAYTIMEGOALS_VERSION%.0}.zip"

rm -f \
    "$BUNDLE_ZIP" \
    "$ACCOUNT_ZIP" \
    "$CENTER_ZIP" \
    "$WEB_ZIP" \
    "$PTG_ZIP"

python3 "$SCRIPT_DIR/create-native-zips.py" \
    --stage "$STAGE_ROOT" \
    --runtime "$ASF_RUNTIME" \
    --out "$OUT_PARENT" \
    --suite-version "$CONTROL_SUITE_VERSION" \
    --playtimegoals-version "$PLAYTIMEGOALS_VERSION"

for archive in \
    "$BUNDLE_ZIP" \
    "$ACCOUNT_ZIP" \
    "$CENTER_ZIP" \
    "$WEB_ZIP" \
    "$PTG_ZIP"
do
    [[ -s "$archive" ]] || {
        echo \
            "native release archive missing: $archive" \
            >&2
        exit 9
    }
done

METADATA="$OUT_PARENT/CONTROL-SUITE-METADATA.json"
SHA256SUMS="$OUT_PARENT/SHA256SUMS"

python3 - \
    "$METADATA" \
    "$CONTROL_SUITE_VERSION" \
    "$CONTROL_MODULE_VERSION" \
    "$PLAYTIMEGOALS_VERSION" \
    "$PLAYTIMEGOALS_COMMIT" \
    "$ASF_VERSION" \
    "$ASF_COMMIT" \
    "$ASF_PATCH_SHA256" \
    "$ASF_UI_COMMIT" \
    "$DOTNET_SDK_VERSION" \
    "$(basename "$BUNDLE_ZIP")" \
    "$(basename "$ACCOUNT_ZIP")" \
    "$(basename "$CENTER_ZIP")" \
    "$(basename "$WEB_ZIP")" \
    <<'PY'
import json
import sys
from pathlib import Path

(
    metadata_path,
    suite_version,
    module_version,
    ptg_version,
    ptg_commit,
    asf_version,
    asf_commit,
    asf_patch_sha256,
    asf_ui_commit,
    sdk_version,
    bundle_zip,
    account_zip,
    center_zip,
    web_zip,
) = sys.argv[1:]

payload = {
    "schemaVersion": 1,
    "release": {
        "controlSuiteVersion": suite_version,
        "controlModuleVersion": module_version,
        "playtimeGoalsVersion": ptg_version,
    },
    "targets": {
        "asfVersion": asf_version,
        "asfCommit": asf_commit,
        "asfPatchSha256": asf_patch_sha256,
        "asfUiCommit": asf_ui_commit,
        "playtimeGoalsCommit": ptg_commit,
        "dotnetSdkVersion": sdk_version,
    },
    "install": {
        "extractInto": "<ASF>/",
        "webPath": "/Control/",
    },
    # Public Control Suite release assets only.
    #
    # The standalone PlaytimeGoals ZIP is still produced by the
    # canonical build for byte-provenance verification, but belongs
    # to the separate PlaytimeGoals public release.
    "artifacts": [
        bundle_zip,
        account_zip,
        center_zip,
        web_zip,
    ],
}

Path(metadata_path).write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY

(
    cd "$OUT_PARENT" || exit 1

    # SHA256SUMS is the public Control Suite release manifest.
    # PlaytimeGoals publishes its standalone ZIP from its own release.
    sha256sum \
        "$(basename "$BUNDLE_ZIP")" \
        "$(basename "$ACCOUNT_ZIP")" \
        "$(basename "$CENTER_ZIP")" \
        "$(basename "$WEB_ZIP")" \
        "CONTROL-SUITE-METADATA.json" \
        > "SHA256SUMS"

    sha256sum \
        -c \
        "SHA256SUMS"
)

python3 "$SCRIPT_DIR/verify-release-artifacts.py" \
    --build-root "$ASF_ROOT" \
    --artifacts "$OUT_PARENT" \
    --pins "$SUITE_ROOT/release/pins.env"

echo
echo "Native ASF release artifacts:"
printf '  %s\n' \
    "$BUNDLE_ZIP" \
    "$ACCOUNT_ZIP" \
    "$CENTER_ZIP" \
    "$WEB_ZIP" \
    "$PTG_ZIP" \
    "$METADATA" \
    "$SHA256SUMS"
