#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo '=== ASF CONTROL SUITE 1.0 SANDBOX SUITE ==='
python tests/static_contracts.py
node tests/control_core.test.js
python tests/ui_integration.py
bash tests/phone_transaction.test.sh
node --check ControlWeb/www/i18n.js
node --check ControlWeb/www/core.js
node --check ControlWeb/www/app.js
for f in scripts/*.sh installer/*.sh tests/*.sh; do bash -n "$f"; done

echo 'ALL SANDBOX TESTS: PASS'
