#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${1:-$(pwd)}"
PATCH="${2:-$(cd "$(dirname "$0")/../.." && pwd)/patches/asf/0001-headless-qr-ipc.patch}"
ASF_PATCH_SHA256="650b7cf9109d7c4d5d9d2a8d6bd37f1a591b920ad918eecebaed9ee0ad0a1432"

[[ -d "$ROOT/.git" ]] || { echo "ASF git worktree not found: $ROOT" >&2; exit 2; }
[[ -f "$PATCH" ]] || { echo "ASF patch missing: $PATCH" >&2; exit 3; }

actual="$(sha256sum "$PATCH" | awk '{print $1}')"
[[ "$actual" == "$ASF_PATCH_SHA256" ]] || {
  echo "ASF patch digest mismatch: expected $ASF_PATCH_SHA256 got $actual" >&2
  exit 4
}

cd "$ROOT"

git apply --check "$PATCH"
git apply "$PATCH"
git diff --check -- ArchiSteamFarm/Steam/Bot.cs

grep -Fq 'Control Suite compatibility: in headless/service mode' ArchiSteamFarm/Steam/Bot.cs
grep -Fq 'RequiredInput = ASF.EUserInputType.QrCodeLogin;' ArchiSteamFarm/Steam/Bot.cs
grep -Fq 'QrCodeLoginInput = null;' ArchiSteamFarm/Steam/Bot.cs

echo "ASF HEADLESS QR PATCH: APPLIED"
