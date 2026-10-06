from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

errors = []

pins_file = ROOT / "release" / "pins.env"
generator = ROOT / "scripts" / "dev" / "generate-build-info.py"
plugin = ROOT / "src" / "ControlCenter" / "ControlCenterPlugin.cs"
gitignore = ROOT / ".gitignore"
prepare = ROOT / "scripts" / "build" / "prepare-release-worktree.sh"

pins = {}

if pins_file.is_file():
    for raw in pins_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            errors.append("invalid release/pins.env entry")
            continue

        key, value = line.split("=", 1)
        pins[key] = value
else:
    errors.append("release/pins.env missing")


required_pins = (
    "CONTROL_SUITE_VERSION",
    "CONTROL_MODULE_VERSION",
    "ASF_VERSION",
    "ASF_COMMIT",
    "ASF_UI_COMMIT",
    "PLAYTIMEGOALS_VERSION",
    "PLAYTIMEGOALS_COMMIT",
    "DOTNET_SDK_VERSION",
)

for key in required_pins:
    if key not in pins:
        errors.append(f"missing canonical pin: {key}")


if not generator.is_file():
    errors.append(
        "scripts/dev/generate-build-info.py missing"
    )

if not plugin.is_file():
    errors.append(
        "ControlCenterPlugin.cs missing"
    )
else:
    text = plugin.read_text(encoding="utf-8")

    required_refs = (
        "BuildInfo.ControlSuiteVersion",
        "BuildInfo.ControlModuleVersion",
        "BuildInfo.TargetAsfVersion",
        "BuildInfo.TargetAsfCommit",
        "BuildInfo.TargetAsfUiCommit",
        "BuildInfo.TargetPlaytimeGoalsVersion",
        "BuildInfo.TargetPlaytimeGoalsCommit",
    )

    for reference in required_refs:
        if reference not in text:
            errors.append(
                f"ControlCenterPlugin does not use {reference}"
            )

    # Runtime source must not own the canonical literal values.
    for key in (
        "ASF_VERSION",
        "ASF_COMMIT",
        "PLAYTIMEGOALS_VERSION",
        "PLAYTIMEGOALS_COMMIT",
    ):
        value = pins.get(key)

        if value and value in text:
            errors.append(
                f"ControlCenterPlugin hardcodes {key}"
            )


# Runtime/API/UI metadata consumers must not duplicate canonical release pins.
runtime_metadata_consumers = (
    ROOT / "src" / "ControlCenter" / "ControlCenterPlugin.cs",
    ROOT / "src" / "ControlCenter" / "ControlCenterController.cs",
    ROOT / "src" / "ControlWeb" / "www" / "app.js",
)

for runtime_path in runtime_metadata_consumers:
    if not runtime_path.is_file():
        errors.append(
            f"runtime metadata consumer missing: {runtime_path.relative_to(ROOT)}"
        )
        continue

    runtime_text = runtime_path.read_text(encoding="utf-8")

    for key in (
        "ASF_VERSION",
        "ASF_COMMIT",
        "ASF_UI_COMMIT",
        "PLAYTIMEGOALS_VERSION",
        "PLAYTIMEGOALS_COMMIT",
        "CONTROL_SUITE_VERSION",
        "CONTROL_MODULE_VERSION",
    ):
        value = pins.get(key)

        if value and value in runtime_text:
            errors.append(
                f"{runtime_path.relative_to(ROOT)} hardcodes {key}"
            )


if gitignore.is_file():
    ignore_text = gitignore.read_text(encoding="utf-8")

    if "Generated/" not in ignore_text:
        errors.append(
            "Generated/ missing from .gitignore"
        )
else:
    errors.append(".gitignore missing")


if prepare.is_file():
    prepare_text = prepare.read_text(encoding="utf-8")

    if "generate-build-info.py" not in prepare_text:
        errors.append(
            "release preparation does not generate BuildInfo"
        )
else:
    errors.append(
        "prepare-release-worktree.sh missing"
    )


# Generated code must not be committed to Git.
generated = (
    ROOT
    / "src"
    / "ControlCenter"
    / "Generated"
    / "BuildInfo.cs"
)

if generated.exists():
    errors.append(
        "generated BuildInfo.cs exists in source worktree"
    )


if errors:
    print("BUILDINFO CONTRACT: FAIL")

    for error in errors:
        print(" -", error)

    sys.exit(1)

print("BUILDINFO CONTRACT: PASS")
