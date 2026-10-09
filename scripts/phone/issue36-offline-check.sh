#!/usr/bin/env bash
# Offline developer acceptance for Issue #36. HOST ONLY, NO ADB OR LIVE TMUX.
# Runs test mocks and bash parsing; never deploys or touches Mi Max 2.
set -Eeuo pipefail
umask 077

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$ROOT"
PYTHON="${ASFC_PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || {
  echo 'ISSUE36_PYTHON_MISSING'; exit 2;
}
export PYTHONDONTWRITEBYTECODE=1

echo '=== ISSUE #36 OFFLINE CHECK (NO DEVICE CONTACT) ==='
for sh in \
  scripts/phone/asf-only-launcher.sh \
  scripts/phone/prepare-asf-only-adapter.sh \
  scripts/phone/asf-isolated-tmux-rehearsal.sh \
  scripts/phone/asf-isolated-rehearsal-preflight.sh \
  scripts/phone/phone-guarded-rollback-v3.sh \
  scripts/phone/issue36-offline-check.sh; do
  bash -n "$sh" || { echo 'ISSUE36_BASH_SYNTAX_FAIL'; exit 3; }
done
echo 'ISSUE36_BASH_SYNTAX=PASS'

for testfile in \
  tests/asf_only_launcher.test.py \
  tests/prepare_asf_only_adapter.test.py \
  tests/asf_only_synthetic_rehearsal.test.py \
  tests/asf_isolated_tmux_rehearsal.test.py \
  tests/phone_guarded_rollback.test.py; do
  echo "ISSUE36_TEST=${testfile}"
  "$PYTHON" -B -S "$testfile" || { echo 'ISSUE36_OFFLINE_TESTS=FAIL'; exit 4; }
done

echo 'ISSUE36_OFFLINE_TESTS=PASS'
echo 'LIVE_ROLLBACK=NOT_ATTEMPTED'
echo 'ANDROID_PROOT_ADAPTER=NOT_TESTED'
echo 'DEVICE_DEPLOYMENT=NOT_ATTEMPTED'
