#!/usr/bin/env bash
set -Eeuo pipefail

ASF_ROOT="${1:-$(pwd)}"
OUT_PARENT="${2:-$ASF_ROOT/artifacts}"
DIST_NAME="asf-control-suite-v1.0-dist"
OUT="$OUT_PARENT/$DIST_NAME"
ASF_COMMIT="27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad"
ASF_UI_COMMIT="2b36125533f41e624b2fdcdec44f37ad60c7daaa"
PTG_COMMIT="fa959d3d4ffd09f7fd30e9ee8599aa5004b67033"

cd "$ASF_ROOT"
[[ "$(git rev-parse HEAD)" == "$ASF_COMMIT" ]] || { echo "wrong ASF HEAD" >&2; exit 2; }
[[ "$(git -C ASF-ui rev-parse HEAD)" == "$ASF_UI_COMMIT" ]] || { echo "wrong ASF-ui HEAD" >&2; exit 3; }

rm -rf "$OUT"
mkdir -p "$OUT/plugins"/{PlaytimeGoals,AccountManager,ControlCenter,ControlWeb} "$OUT/installer"
cp PlaytimeGoals/bin/Release/net10.0/PlaytimeGoals.dll "$OUT/plugins/PlaytimeGoals/"
cp AccountManager/bin/Release/net10.0/AccountManager.dll "$OUT/plugins/AccountManager/"
cp ControlCenter/bin/Release/net10.0/ControlCenter.dll "$OUT/plugins/ControlCenter/"
cp ControlWeb/bin/Release/net10.0/ControlWeb.dll "$OUT/plugins/ControlWeb/"
cp -a ControlWeb/bin/Release/net10.0/www "$OUT/plugins/ControlWeb/www"

SUITE_SOURCE="${CONTROL_SUITE_SOURCE:-}"
[[ -n "$SUITE_SOURCE" && -f "$SUITE_SOURCE/installer/phone-transaction.sh" && -f "$SUITE_SOURCE/installer/phone-rollback-core.sh" ]] || {
  echo "set CONTROL_SUITE_SOURCE to the asf-control-suite-v1.0 source directory" >&2
  exit 4
}
cp "$SUITE_SOURCE/installer/phone-transaction.sh" "$SUITE_SOURCE/installer/phone-rollback-core.sh" "$OUT/installer/"
chmod 0755 "$OUT/installer/phone-transaction.sh" "$OUT/installer/phone-rollback-core.sh"

cat > "$OUT/BUILD-METADATA.txt" <<TXT
Release: ASF Control Suite v1.0
Control modules: 1.0.0.0
PlaytimeGoals: 0.5.0.0
PlaytimeGoals commit: $PTG_COMMIT
ASF version: 6.3.10.3
ASF commit: $(git rev-parse HEAD)
ASF-ui commit: $(git -C ASF-ui rev-parse HEAD)
.NET SDK: $(dotnet --version)
Build UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Install target: /opt/asf
Web path: /Control/
TXT

cat > "$OUT/INSTALL-LAYOUT.txt" <<'TXT'
plugins/PlaytimeGoals/PlaytimeGoals.dll
plugins/AccountManager/AccountManager.dll
plugins/ControlCenter/ControlCenter.dll
plugins/ControlWeb/ControlWeb.dll
plugins/ControlWeb/www/index.html
plugins/ControlWeb/www/i18n.js
plugins/ControlWeb/www/core.js
plugins/ControlWeb/www/qrcode.min.js
plugins/ControlWeb/www/qrcode.LICENSE.txt
plugins/ControlWeb/www/app.js
plugins/ControlWeb/www/app.css

No /opt/asf/www files are replaced. Existing config/database files remain in /opt/asf/config.
TXT

(
  cd "$OUT"
  find plugins installer BUILD-METADATA.txt INSTALL-LAYOUT.txt -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS
)

mkdir -p "$OUT_PARENT"
ARCHIVE="$OUT_PARENT/$DIST_NAME.tar.gz"
rm -f "$ARCHIVE"
tar -C "$OUT_PARENT" -czf "$ARCHIVE" "$DIST_NAME"
printf 'Archive: %s\n' "$ARCHIVE"
sha256sum "$ARCHIVE"
