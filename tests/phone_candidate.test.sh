#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ART="$TMP/artifacts"
OUT="$TMP/out"
mkdir -p "$ART" "$OUT"

# shellcheck disable=SC1091
. "$ROOT/scripts/build/pins.sh"
load_release_pins "$ROOT/release/pins.env"

python3 - "$ART" "$CONTROL_SUITE_VERSION" <<'PY'
import json
import pathlib
import stat
import sys
import zipfile

root = pathlib.Path(sys.argv[1])
version = sys.argv[2]
bundle = root / f"ASF-Control-Suite-v{version}.zip"

payloads = {
    "ArchiSteamFarm": b"runtime\n",
    "plugins/PlaytimeGoals/PlaytimeGoals.dll": b"ptg\n",
    "plugins/AccountManager/AccountManager.dll": b"account\n",
    "plugins/ControlCenter/ControlCenter.dll": b"center\n",
    "plugins/ControlWeb/ControlWeb.dll": b"web\n",
    "plugins/ControlWeb/www/index.html": b"<html></html>\n",
    "plugins/ControlWeb/www/i18n.js": b"i18n\n",
    "plugins/ControlWeb/www/core.js": b"core\n",
    "plugins/ControlWeb/www/qrcode.min.js": b"qr\n",
    "plugins/ControlWeb/www/qrcode.LICENSE.txt": b"license\n",
    "plugins/ControlWeb/www/app.js": b"app\n",
    "plugins/ControlWeb/www/app.css": b"css\n",
}

with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for name, data in payloads.items():
        info = zipfile.ZipInfo(name)
        info.date_time = (1980, 1, 1, 0, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        mode = stat.S_IFREG | (0o755 if name == "ArchiSteamFarm" else 0o644)
        info.external_attr = mode << 16
        z.writestr(info, data)
PY

cat > "$ART/CONTROL-SUITE-METADATA.json" <<JSON
{
  "schemaVersion": 1,
  "release": {
    "controlModuleVersion": "$CONTROL_MODULE_VERSION",
    "controlSuiteVersion": "$CONTROL_SUITE_VERSION",
    "playtimeGoalsVersion": "$PLAYTIMEGOALS_VERSION"
  },
  "targets": {
    "asfCommit": "$ASF_COMMIT",
    "asfPatchSha256": "$ASF_PATCH_SHA256",
    "asfUiCommit": "$ASF_UI_COMMIT",
    "asfVersion": "$ASF_VERSION",
    "dotnetSdkVersion": "$DOTNET_SDK_VERSION",
    "playtimeGoalsCommit": "$PLAYTIMEGOALS_COMMIT"
  },
  "install": {
    "extractInto": "<ASF>/",
    "webPath": "/",
    "canonicalControlPath": "/Control/"
  },
  "artifacts": [
    "ASF-Control-Suite-v$CONTROL_SUITE_VERSION.zip"
  ]
}
JSON

(
  cd "$ART"
  sha256sum     "ASF-Control-Suite-v$CONTROL_SUITE_VERSION.zip"     CONTROL-SUITE-METADATA.json     > SHA256SUMS
)

DIST_NAME="asf-control-suite-v${CONTROL_SUITE_VERSION}-dist"
ARCHIVE="$OUT/$DIST_NAME.tar.gz"

bash "$ROOT/scripts/phone/make-phone-candidate.sh" "$ART" "$OUT"
FIRST="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
cp "$ARCHIVE" "$TMP/first.tar.gz"

bash "$ROOT/scripts/phone/make-phone-candidate.sh" "$ART" "$OUT"
SECOND="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
[[ "$FIRST" == "$SECOND" ]]

mkdir -p "$TMP/extract"
tar -xzf "$ARCHIVE" -C "$TMP/extract"
DIST="$TMP/extract/$DIST_NAME"

[[ -x "$DIST/ArchiSteamFarm" ]]
[[ -x "$DIST/installer/phone-transaction.sh" ]]
grep -Fq "ASF commit: $ASF_COMMIT" "$DIST/BUILD-METADATA.txt"
grep -Fq "PlaytimeGoals commit: $PLAYTIMEGOALS_COMMIT" "$DIST/BUILD-METADATA.txt"
(
  cd "$DIST"
  sha256sum -c SHA256SUMS
)

echo "PHONE CANDIDATE TEST: PASS"
