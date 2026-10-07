from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATCH_REL = "patches/asf/0001-headless-qr-ipc.patch"
PINS = ROOT / "release" / "pins.env"

pins = {}
for raw in PINS.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    key, value = line.split("=", 1)
    pins[key] = value

expected = pins.get("ASF_PATCH_SHA256", "")
if not re.fullmatch(r"[0-9a-f]{64}", expected):
    print("ASF PATCH PROVENANCE: FAIL")
    print(" - invalid ASF_PATCH_SHA256 pin")
    raise SystemExit(1)

result = subprocess.run(
    ["git", "-C", str(ROOT), "show", f"HEAD:{PATCH_REL}"],
    check=True,
    stdout=subprocess.PIPE,
)

actual = sha256(result.stdout).hexdigest()

if actual != expected:
    print("ASF PATCH PROVENANCE: FAIL")
    print(f" - expected: {expected}")
    print(f" - actual:   {actual}")
    raise SystemExit(1)

print("ASF PATCH PROVENANCE: PASS")
