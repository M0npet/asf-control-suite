from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "scripts/build/make-release.sh"
text = path.read_text(encoding="utf-8")

errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

require(
    'PYTHON="${CONTROL_PYTHON:-python3}"' in text,
    "make-release.sh does not honor CONTROL_PYTHON",
)

for script in (
    "tests/static_contracts.py",
    "tests/pins_single_source.test.py",
    "tests/ui_integration.py",
):
    require(
        f'"$PYTHON" "$SUITE_ROOT/{script}"' in text,
        f"{script} is not run through the canonical Python interpreter",
    )

require(
    'python3 "$SUITE_ROOT/tests/' not in text,
    "make-release.sh still hardcodes python3 for test execution",
)

if errors:
    print("RELEASE PYTHON RUNTIME CONTRACT: FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("RELEASE PYTHON RUNTIME CONTRACT: PASS")
