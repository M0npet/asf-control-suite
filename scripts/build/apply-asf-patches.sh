#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ROOT="${1:-$(pwd)}"
PATCH_REL="patches/asf/0001-headless-qr-ipc.patch"
PATCH_OVERRIDE="${2:-}"
PATCH=""
PATCH_TMP=""

cleanup() {
  if [[ -n "$PATCH_TMP" ]]; then
    rm -f "$PATCH_TMP"
  fi
}
trap cleanup EXIT

# shellcheck disable=SC1091
. "$SCRIPT_DIR/pins.sh"
load_release_pins "$SUITE_ROOT/release/pins.env"

[[ "$(git -C "$ROOT" rev-parse --is-inside-work-tree 2>/dev/null || true)" == "true" ]] || {
  echo "ASF git worktree not found: $ROOT" >&2
  exit 2
}

if [[ -n "$PATCH_OVERRIDE" ]]; then
  PATCH="$PATCH_OVERRIDE"
  [[ -f "$PATCH" ]] || { echo "ASF patch missing: $PATCH" >&2; exit 3; }
else
  [[ "$(git -C "$SUITE_ROOT" rev-parse --is-inside-work-tree 2>/dev/null || true)" == "true" ]] || {
    echo "Control Suite git worktree not found: $SUITE_ROOT" >&2
    exit 3
  }

  PATCH_TMP="$(mktemp)"
  git -C "$SUITE_ROOT" show "HEAD:$PATCH_REL" > "$PATCH_TMP"
  PATCH="$PATCH_TMP"
fi

actual="$(sha256sum "$PATCH" | awk '{print $1}')"
[[ "$actual" == "$ASF_PATCH_SHA256" ]] || {
  echo "ASF patch digest mismatch: expected $ASF_PATCH_SHA256 got $actual" >&2
  exit 4
}

cd "$ROOT"

git apply --check "$PATCH"
git apply "$PATCH"
git diff --check -- \
  ArchiSteamFarm/Steam/Bot.cs \
  ArchiSteamFarm/Steam/Storage/BotDatabase.cs

grep -Fq 'Control Suite compatibility: in headless/service mode' ArchiSteamFarm/Steam/Bot.cs
grep -Fq 'RequiredInput = ASF.EUserInputType.QrCodeLogin;' ArchiSteamFarm/Steam/Bot.cs
grep -Fq 'QrCodeLoginInput = null;' ArchiSteamFarm/Steam/Bot.cs
grep -Fq 'ControlSuiteQrSteamLogin' ArchiSteamFarm/Steam/Storage/BotDatabase.cs
grep -Fq 'BotDatabase.QrSteamLogin = pollResult.AccountName;' ArchiSteamFarm/Steam/Bot.cs

echo "ASF HEADLESS QR PATCH: APPLIED"
