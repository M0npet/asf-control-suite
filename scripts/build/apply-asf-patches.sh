#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${1:-$(pwd)}"
PATCH="${2:-$(cd "$(dirname "$0")/../.." && pwd)/patches/asf/0001-headless-qr-ipc.patch}"
ASF_PATCH_SHA256="320b6873713c36a844ed2cc764b8d7569752d736e2db0dc6ab41f3e4ea14f728"

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
