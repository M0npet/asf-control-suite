#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${CONTROL_PYTHON:-python3}"

echo '=== ASF CONTROL SUITE 1.0 SANDBOX SUITE ==='
"$PYTHON" tests/migration_structure.test.py
"$PYTHON" tests/pins_single_source.test.py
"$PYTHON" tests/build_info_contract.test.py
"$PYTHON" tests/auth_memory_only.test.py
"$PYTHON" tests/dotnet_supply_chain.test.py
"$PYTHON" tests/native_zip_packaging.test.py
"$PYTHON" tests/release_provenance.test.py
"$PYTHON" tests/public_release_contract.test.py
"$PYTHON" tests/build_info_generator.test.py
bash tests/pins_parser.test.sh
"$PYTHON" tests/static_contracts.py
node tests/control_core.test.js
"$PYTHON" tests/ui_integration.py
bash tests/phone_transaction.test.sh
node --check src/ControlWeb/www/i18n.js
node --check src/ControlWeb/www/core.js
node --check src/ControlWeb/www/app.js
for f in scripts/build/*.sh scripts/phone/*.sh installer/*.sh tests/*.sh; do bash -n "$f"; done

echo 'ALL SANDBOX TESTS: PASS'
