#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARTIFACTS="${1:-}"
OUT_PARENT="${2:-$SUITE_ROOT/artifacts}"
DIST_NAME="asf-control-suite-v1.0-dist"

die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ -n "$ARTIFACTS" && -d "$ARTIFACTS" ]] || die "usage: $0 /path/to/release-artifacts [output-dir]"
command -v unzip >/dev/null 2>&1 || die "unzip not found"
command -v sha256sum >/dev/null 2>&1 || die "sha256sum not found"
command -v gzip >/dev/null 2>&1 || die "gzip not found"
command -v tar >/dev/null 2>&1 || die "tar not found"

# shellcheck disable=SC1091
. "$SUITE_ROOT/scripts/build/pins.sh"
load_release_pins "$SUITE_ROOT/release/pins.env"

BUNDLE="$ARTIFACTS/ASF-Control-Suite-v$CONTROL_SUITE_VERSION.zip"
META="$ARTIFACTS/CONTROL-SUITE-METADATA.json"
PUBLIC_SUMS="$ARTIFACTS/SHA256SUMS"

[[ -s "$BUNDLE" && -s "$META" && -s "$PUBLIC_SUMS" ]] || die "canonical release artifacts missing"

(
  cd "$ARTIFACTS"
  sha256sum -c SHA256SUMS
)

mkdir -p "$OUT_PARENT"
WORK="$(mktemp -d "$OUT_PARENT/.phone-candidate.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
DIST="$WORK/$DIST_NAME"
mkdir -p "$DIST"

unzip -q "$BUNDLE" -d "$DIST"
[[ -s "$DIST/ArchiSteamFarm" ]] || die "bundle runtime missing"
chmod 0755 "$DIST/ArchiSteamFarm"

mkdir -p "$DIST/installer"
cp "$SUITE_ROOT/installer/phone-transaction.sh" "$DIST/installer/phone-transaction.sh"
cp "$SUITE_ROOT/installer/phone-rollback-core.sh" "$DIST/installer/phone-rollback-core.sh"
chmod 0755 "$DIST/installer/"*.sh

python3 - "$META" "$DIST/BUILD-METADATA.txt" <<'PY'
import json
import pathlib
import sys

meta_path = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
meta = json.loads(meta_path.read_text(encoding="utf-8"))

release = meta["release"]
targets = meta["targets"]

rows = [
    f"Control Suite: {release['controlSuiteVersion']}",
    f"Control modules: {release['controlModuleVersion']}",
    f"ASF: {targets['asfVersion']}",
    f"ASF commit: {targets['asfCommit']}",
    f"ASF patch SHA256: {targets['asfPatchSha256']}",
    f"ASF-ui commit: {targets['asfUiCommit']}",
    f"PlaytimeGoals: {release['playtimeGoalsVersion']}",
    f"PlaytimeGoals commit: {targets['playtimeGoalsCommit']}",
    f".NET SDK: {targets['dotnetSdkVersion']}",
]
out.write_text("\n".join(rows) + "\n", encoding="utf-8")
PY

cat > "$DIST/INSTALL-LAYOUT.txt" <<'TXT'
ArchiSteamFarm -> /opt/asf/ArchiSteamFarm
plugins/PlaytimeGoals -> /opt/asf/plugins/PlaytimeGoals
plugins/AccountManager -> /opt/asf/plugins/AccountManager
plugins/ControlCenter -> /opt/asf/plugins/ControlCenter
plugins/ControlWeb -> /opt/asf/plugins/ControlWeb
installer/phone-transaction.sh -> transactional phone installer
installer/phone-rollback-core.sh -> rollback core
TXT

(
  cd "$DIST"
  find . -type f ! -name SHA256SUMS -print0 |
    sort -z |
    xargs -0 sha256sum |
    sed 's#  \./#  #' > SHA256SUMS
  sha256sum -c SHA256SUMS
)

ARCHIVE="$OUT_PARENT/$DIST_NAME.tar.gz"
rm -f "$ARCHIVE"
(
  cd "$WORK"
  tar     --sort=name     --mtime='UTC 1970-01-01'     --owner=0     --group=0     --numeric-owner     -cf -     "$DIST_NAME"
) | gzip -n > "$ARCHIVE"

[[ -s "$ARCHIVE" ]] || die "phone candidate archive missing"
ARCHIVE_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
BUNDLE_SHA="$(sha256sum "$BUNDLE" | awk '{print $1}')"

printf 'PHONE CANDIDATE READY\n'
printf 'Archive: %s\n' "$ARCHIVE"
printf 'Archive SHA256: %s\n' "$ARCHIVE_SHA"
printf 'Bundle SHA256: %s\n' "$BUNDLE_SHA"
