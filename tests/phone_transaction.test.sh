#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TX="$ROOT/installer/phone-transaction.sh"
RB="$ROOT/installer/phone-rollback-core.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

assert_headless_true() {
  python3 - "$1" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
assert isinstance(data, dict), data
assert data.get("Headless") is True, data
PY
}

make_dist() {
  local dist="$1"
  mkdir -p "$dist/plugins"/{PlaytimeGoals,AccountManager,ControlCenter,ControlWeb/www} "$dist/installer"
  printf '#!/bin/sh\n# new-core\nexit 0\n' > "$dist/ArchiSteamFarm"
  chmod 0755 "$dist/ArchiSteamFarm"
  printf 'new-ptg\n' > "$dist/plugins/PlaytimeGoals/PlaytimeGoals.dll"
  printf 'new-account\n' > "$dist/plugins/AccountManager/AccountManager.dll"
  printf 'new-control\n' > "$dist/plugins/ControlCenter/ControlCenter.dll"
  printf 'new-web\n' > "$dist/plugins/ControlWeb/ControlWeb.dll"
  for f in index.html i18n.js core.js qrcode.min.js qrcode.LICENSE.txt app.js app.css; do printf 'asset-%s\n' "$f" > "$dist/plugins/ControlWeb/www/$f"; done
  cp "$TX" "$RB" "$dist/installer/"
  cat > "$dist/BUILD-METADATA.txt" <<'TXT'
ASF commit: 27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad
PlaytimeGoals commit: fa959d3d4ffd09f7fd30e9ee8599aa5004b67033
TXT
  printf 'layout\n' > "$dist/INSTALL-LAYOUT.txt"
  (cd "$dist"; find plugins installer BUILD-METADATA.txt INSTALL-LAYOUT.txt -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
}

make_asf() {
  local asf="$1"
  mkdir -p "$asf/plugins"/{PlaytimeGoals,AccountManager,ControlCenter,ControlWeb/www} "$asf/config" "$asf/www"
  printf '#!/bin/sh\n# old-core\nexit 0\n' > "$asf/ArchiSteamFarm"
  chmod 0755 "$asf/ArchiSteamFarm"
  printf 'old-ptg\n' > "$asf/plugins/PlaytimeGoals/PlaytimeGoals.dll"
  printf 'old-account\n' > "$asf/plugins/AccountManager/AccountManager.dll"
  printf 'old-control\n' > "$asf/plugins/ControlCenter/ControlCenter.dll"
  printf 'old-web\n' > "$asf/plugins/ControlWeb/ControlWeb.dll"
  printf 'old-asset\n' > "$asf/plugins/ControlWeb/www/index.html"
  cat > "$asf/www/index.html" <<'HTML'
<!doctype html>
<html><head><title>Stock ASF-ui</title></head><body><div id="app"></div></body></html>
HTML
  printf '{"safe":true}\n' > "$asf/config/AccountManager.defaults.json"
  cat > "$asf/config/ASF.json" <<'JSON'
{
  "IPC": true,
  "IPCPassword": "preserve-me",
  "IPCPasswordFormat": 1,
  "Headless": false,
  "CustomInvariant": {
    "Nested": "preserve-me-too"
  }
}
JSON
  chmod 0600 "$asf/config/ASF.json"
}

DIST="$TMP/dist"; make_dist "$DIST"

# Unsafe payload nodes (e.g. symlinks) must be rejected before any mutation.
BAD="$TMP/dist-unsafe"; cp -a "$DIST" "$BAD"
ln -s /tmp "$BAD/plugins/ControlWeb/www/unsafe-link"
ASF_BAD="$TMP/asf-unsafe"; make_asf "$ASF_BAD"
set +e
CONTROL_ASF_ROOT="$ASF_BAD" CONTROL_SKIP_PROCESS=1 CONTROL_BACKUP_ID=test-unsafe bash "$TX" "$BAD" >/tmp/control-suite-unsafe.out 2>/tmp/control-suite-unsafe.err
unsafe_rc=$?
set -e
[[ "$unsafe_rc" -ne 0 ]]
grep -qx 'old-ptg' "$ASF_BAD/plugins/PlaytimeGoals/PlaytimeGoals.dll"
[[ ! -d "$ASF_BAD/backups/control-suite/test-unsafe" ]]

# Successful transaction + backup creation + phone headless invariant.
ASF1="$TMP/asf-success"; make_asf "$ASF1"
ASF1_ORIGINAL_SHA="$(sha256sum "$ASF1/config/ASF.json" | awk '{print $1}')"
CONTROL_ASF_ROOT="$ASF1" CONTROL_SKIP_PROCESS=1 CONTROL_BACKUP_ID=test-success bash "$TX" "$DIST"
grep -q '# new-core' "$ASF1/ArchiSteamFarm"
[[ -x "$ASF1/ArchiSteamFarm" ]]
grep -qx 'new-ptg' "$ASF1/plugins/PlaytimeGoals/PlaytimeGoals.dll"
grep -qx 'new-account' "$ASF1/plugins/AccountManager/AccountManager.dll"
grep -q '# old-core' "$ASF1/backups/control-suite/test-success/ArchiSteamFarm"
grep -qx 'old-ptg' "$ASF1/backups/control-suite/test-success/plugins/PlaytimeGoals/PlaytimeGoals.dll"
[[ -s "$ASF1/control-suite/installed/SHA256SUMS" ]]
[[ "$(cat "$ASF1/backups/control-suite/LAST_BACKUP")" == test-success ]]
assert_headless_true "$ASF1/config/ASF.json"
grep -q '"IPCPassword": "preserve-me"' "$ASF1/config/ASF.json"
grep -q '"Nested": "preserve-me-too"' "$ASF1/config/ASF.json"
[[ "$(stat -c '%a' "$ASF1/config/ASF.json")" == 600 ]]
[[ "$(sha256sum "$ASF1/backups/control-suite/test-success/ASF.json" | awk '{print $1}')" == "$ASF1_ORIGINAL_SHA" ]]
grep -Fq 'data-asf-control-suite-root="1"' "$ASF1/www/index.html"
grep -Fq "params.get('asfui') !== '1'" "$ASF1/www/index.html"
grep -Fq "window.location.replace('/Control/' + window.location.search + window.location.hash)" "$ASF1/www/index.html"
grep -Fq '<title>Stock ASF-ui</title>' "$ASF1/backups/control-suite/test-success/www/index.html"
! grep -Fq 'data-asf-control-suite-root="1"' "$ASF1/backups/control-suite/test-success/www/index.html"

# Reinstalling Control Suite keeps the root takeover idempotent.
CONTROL_ASF_ROOT="$ASF1" CONTROL_SKIP_PROCESS=1 CONTROL_BACKUP_ID=test-repeat bash "$TX" "$DIST"
[[ "$(grep -Fc 'data-asf-control-suite-root="1"' "$ASF1/www/index.html")" == 1 ]]

# Manual rollback restores runtime-managed ASF.json byte-for-byte, but keeps
# AccountManager defaults unless explicitly requested.
printf '{"after_install":true}\n' > "$ASF1/config/AccountManager.defaults.json"
CONTROL_ASF_ROOT="$ASF1" CONTROL_SKIP_PROCESS=1 bash "$RB" test-success
grep -q '# old-core' "$ASF1/ArchiSteamFarm"
grep -qx 'old-ptg' "$ASF1/plugins/PlaytimeGoals/PlaytimeGoals.dll"
grep -q 'after_install' "$ASF1/config/AccountManager.defaults.json"
[[ "$(sha256sum "$ASF1/config/ASF.json" | awk '{print $1}')" == "$ASF1_ORIGINAL_SHA" ]]
grep -Fq '<title>Stock ASF-ui</title>' "$ASF1/www/index.html"
! grep -Fq 'data-asf-control-suite-root="1"' "$ASF1/www/index.html"

# Forced post-swap failure must automatically restore plugin bytes, defaults,
# and the original ASF global config byte-for-byte.
ASF2="$TMP/asf-autorb"; make_asf "$ASF2"
ASF2_ORIGINAL_SHA="$(sha256sum "$ASF2/config/ASF.json" | awk '{print $1}')"
set +e
CONTROL_ASF_ROOT="$ASF2" CONTROL_SKIP_PROCESS=1 CONTROL_TEST_FORCE_FAIL=1 CONTROL_BACKUP_ID=test-fail bash "$TX" "$DIST" >/tmp/control-suite-test.out 2>/tmp/control-suite-test.err
rc=$?
set -e
[[ "$rc" -ne 0 ]]
grep -q '# old-core' "$ASF2/ArchiSteamFarm"
grep -qx 'old-ptg' "$ASF2/plugins/PlaytimeGoals/PlaytimeGoals.dll"
grep -qx 'old-account' "$ASF2/plugins/AccountManager/AccountManager.dll"
grep -q '"safe":true' "$ASF2/config/AccountManager.defaults.json"
[[ "$(sha256sum "$ASF2/config/ASF.json" | awk '{print $1}')" == "$ASF2_ORIGINAL_SHA" ]]
grep -Fq '<title>Stock ASF-ui</title>' "$ASF2/www/index.html"
! grep -Fq 'data-asf-control-suite-root="1"' "$ASF2/www/index.html"
[[ ! -d "$ASF2/control-suite/installed" ]]

# An installation with no pre-existing ASF.json creates the minimum headless
# config, and manual rollback removes it again because it did not exist before.
ASF3="$TMP/asf-no-global-config"; make_asf "$ASF3"
rm -f "$ASF3/config/ASF.json"
CONTROL_ASF_ROOT="$ASF3" CONTROL_SKIP_PROCESS=1 CONTROL_BACKUP_ID=test-no-global-config bash "$TX" "$DIST"
assert_headless_true "$ASF3/config/ASF.json"
[[ -f "$ASF3/backups/control-suite/test-no-global-config/ASF_CONFIG_ABSENT" ]]
CONTROL_ASF_ROOT="$ASF3" CONTROL_SKIP_PROCESS=1 bash "$RB" test-no-global-config
[[ ! -e "$ASF3/config/ASF.json" ]]

echo 'PHONE TRANSACTION TESTS: PASS'
