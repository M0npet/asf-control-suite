from pathlib import Path
import subprocess
import tempfile
import sys


ROOT = Path(__file__).resolve().parents[1]

pins_path = ROOT / "release" / "pins.env"
generator = (
    ROOT
    / "scripts"
    / "dev"
    / "generate-build-info.py"
)

pins = {}

for raw in pins_path.read_text(
    encoding="utf-8"
).splitlines():
    line = raw.strip()

    if not line or line.startswith("#"):
        continue

    key, value = line.split("=", 1)
    pins[key] = value


expected = {
    "ControlSuiteVersion":
        pins["CONTROL_SUITE_VERSION"],

    "ControlModuleVersion":
        pins["CONTROL_MODULE_VERSION"],

    "TargetAsfVersion":
        pins["ASF_VERSION"],

    "TargetAsfCommit":
        pins["ASF_COMMIT"],

    "TargetAsfUiCommit":
        pins["ASF_UI_COMMIT"],

    "TargetPlaytimeGoalsVersion":
        pins["PLAYTIMEGOALS_VERSION"],

    "TargetPlaytimeGoalsCommit":
        pins["PLAYTIMEGOALS_COMMIT"],

    "DotnetSdkVersion":
        pins["DOTNET_SDK_VERSION"],
}


with tempfile.TemporaryDirectory() as temp:
    output = Path(temp) / "Generated" / "BuildInfo.cs"

    subprocess.run(
        [
            sys.executable,
            str(generator),
            str(pins_path),
            str(output),
        ],
        check=True,
        cwd=ROOT,
    )

    text = output.read_text(
        encoding="utf-8"
    )

    for member, value in expected.items():
        expected_line = (
            f'internal const string {member} = "{value}";'
        )

        if expected_line not in text:
            raise SystemExit(
                f"generated BuildInfo missing: {expected_line}"
            )


with tempfile.TemporaryDirectory() as temp:
    bad_pins = Path(temp) / "pins.env"
    output = Path(temp) / "BuildInfo.cs"

    original = pins_path.read_text(
        encoding="utf-8"
    )

    bad_pins.write_text(
        original
        + "UNKNOWN_RELEASE_PIN=value\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(generator),
            str(bad_pins),
            str(output),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode == 0:
        raise SystemExit(
            "generator accepted unknown pin"
        )

    if output.exists():
        raise SystemExit(
            "generator emitted output for invalid pins"
        )


source_generated = (
    ROOT
    / "src"
    / "ControlCenter"
    / "Generated"
    / "BuildInfo.cs"
)

if source_generated.exists():
    raise SystemExit(
        "BuildInfo leaked into source worktree"
    )

print("BUILDINFO GENERATOR TEST: PASS")
