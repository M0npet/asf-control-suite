from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

required_dirs = [
    "src/AccountManager",
    "src/ControlCenter",
    "src/ControlWeb",
    "scripts/build",
    "scripts/dev",
    "scripts/phone",
    "docs/architecture",
    "docs/installation",
    "docs/development",
    "release",
]

required_files = [
    "release/pins.env",
    ".gitignore",
    "SECURITY.md",
]

for rel in required_dirs:
    if not (ROOT / rel).is_dir():
        errors.append(f"missing directory: {rel}/")

for rel in required_files:
    if not (ROOT / rel).is_file():
        errors.append(f"missing file: {rel}")

forbidden_legacy = [
    "AccountManager",
    "ControlCenter",
    "ControlWeb",
    "MANIFEST.sha256",
    "READY_STATUS.md",
    "RUN_NEXT.md",
]

for rel in forbidden_legacy:
    if (ROOT / rel).exists():
        errors.append(f"legacy path still present: {rel}")

if errors:
    print("MIGRATION STRUCTURE CONTRACT: FAIL")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print("MIGRATION STRUCTURE CONTRACT: PASS")
