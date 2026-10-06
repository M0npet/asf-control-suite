from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "release" / "pins.env"

errors = []

required = (
    "CONTROL_SUITE_VERSION",
    "CONTROL_MODULE_VERSION",
    "ASF_VERSION",
    "ASF_COMMIT",
    "ASF_PATCH_SHA256",
    "ASF_UI_COMMIT",
    "PLAYTIMEGOALS_VERSION",
    "PLAYTIMEGOALS_COMMIT",
    "DOTNET_SDK_VERSION",
)

if not PINS.is_file():
    print("PINS SINGLE SOURCE: FAIL")
    print(" - release/pins.env missing")
    raise SystemExit(1)

values = {}

for lineno, raw in enumerate(
    PINS.read_text(encoding="utf-8").splitlines(),
    1,
):
    line = raw.strip()

    if not line or line.startswith("#"):
        continue

    if not re.fullmatch(
        r"[A-Z][A-Z0-9_]*=[A-Za-z0-9._-]+",
        line,
    ):
        errors.append(
            f"invalid pins.env syntax at line {lineno}"
        )
        continue

    key, value = line.split("=", 1)

    if key in values:
        errors.append(
            f"duplicate pin: {key}"
        )

    values[key] = value

for key in required:
    if key not in values:
        errors.append(
            f"missing pin: {key}"
        )

extra = sorted(set(values) - set(required))

if extra:
    errors.append(
        "unexpected pins: " + ", ".join(extra)
    )

validators = {
    "CONTROL_SUITE_VERSION":
        r"\d+\.\d+\.\d+",

    "CONTROL_MODULE_VERSION":
        r"\d+\.\d+\.\d+\.\d+",

    "ASF_VERSION":
        r"\d+\.\d+\.\d+\.\d+",

    "ASF_COMMIT":
        r"[0-9a-f]{40}",

    "ASF_PATCH_SHA256":
        r"[0-9a-f]{64}",

    "ASF_UI_COMMIT":
        r"[0-9a-f]{40}",

    "PLAYTIMEGOALS_VERSION":
        r"\d+\.\d+\.\d+\.\d+",

    "PLAYTIMEGOALS_COMMIT":
        r"[0-9a-f]{40}",

    "DOTNET_SDK_VERSION":
        r"\d+\.\d+\.\d+",
}

for key, pattern in validators.items():
    value = values.get(key)

    if value is not None and not re.fullmatch(pattern, value):
        errors.append(
            f"invalid {key}: {value!r}"
        )


# Phase 3 scope:
# build/release/install tooling may not own literal release pins anymore.
controlled_files = (
    "scripts/build/build-release.sh",
    "scripts/build/make-release.sh",
    "scripts/build/package-release.sh",
    "scripts/build/prepare-release-worktree.sh",
    "scripts/build/apply-asf-patches.sh",
    "installer/phone-transaction.sh",
)

pin_keys_for_tooling = (
    "ASF_VERSION",
    "ASF_COMMIT",
    "ASF_PATCH_SHA256",
    "ASF_UI_COMMIT",
    "PLAYTIMEGOALS_VERSION",
    "PLAYTIMEGOALS_COMMIT",
    "DOTNET_SDK_VERSION",
    "CONTROL_SUITE_VERSION",
    "CONTROL_MODULE_VERSION",
)

for rel in controlled_files:
    path = ROOT / rel

    if not path.is_file():
        errors.append(
            f"missing controlled file: {rel}"
        )
        continue

    text = path.read_text(encoding="utf-8")

    for key in pin_keys_for_tooling:
        value = values.get(key)

        if value and value in text:
            errors.append(
                f"{rel} hardcodes {key}"
            )


# Build scripts must consume the canonical file.
for rel in (
    "scripts/build/build-release.sh",
    "scripts/build/make-release.sh",
    "scripts/build/package-release.sh",
    "scripts/build/prepare-release-worktree.sh",
):
    path = ROOT / rel

    if path.is_file():
        text = path.read_text(encoding="utf-8")

        if "release/pins.env" not in text:
            errors.append(
                f"{rel} does not consume release/pins.env"
            )


# No build script is allowed to source arbitrary shell content from pins.env.
# Phase 3 implementation must use a strict parser/allowlist.
for rel in (
    "scripts/build/build-release.sh",
    "scripts/build/make-release.sh",
    "scripts/build/package-release.sh",
    "scripts/build/prepare-release-worktree.sh",
):
    path = ROOT / rel

    if not path.is_file():
        continue

    text = path.read_text(encoding="utf-8")

    forbidden_patterns = (
        r"\bsource\s+.*pins\.env",
        r"\.\s+.*pins\.env",
    )

    for pattern in forbidden_patterns:
        if re.search(pattern, text):
            errors.append(
                f"{rel} shell-sources pins.env"
            )


if errors:
    print("PINS SINGLE SOURCE: FAIL")

    for error in errors:
        print(" -", error)

    sys.exit(1)

print("PINS SINGLE SOURCE: PASS")
