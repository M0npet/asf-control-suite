from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
requirements = ROOT / "requirements-ci.txt"
dependabot = ROOT / ".github/dependabot.yml"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


require("runs-on: ubuntu-24.04" in workflow, "CI runner must be pinned to ubuntu-24.04")
require(
    "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow,
    "checkout must be pinned to v7.0.1 commit SHA",
)
require(
    "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow,
    "setup-python must be pinned to v7.0.0 commit SHA",
)
require(
    "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020" in workflow,
    "setup-node must be pinned to v7.0.0 commit SHA",
)
require(
    "actions/setup-dotnet@67a3573c9a986a3f9c594539f4ab511d57bb3ce9" in workflow,
    "setup-dotnet must be pinned to the resolved v4 commit SHA",
)
require(
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in workflow,
    "upload-artifact must be pinned to the resolved v4 commit SHA",
)
require(
    "scripts/build/package-release.sh" in workflow
    and "asf-control-suite-artifacts" in workflow
    and "CONTROL-SUITE-COMMIT.txt" in workflow,
    "exact build must package and retain a traceable release candidate",
)
require(
    "steps.pins.outputs.asf_commit" in workflow
    and "steps.pins.outputs.playtimegoals_commit" in workflow
    and "steps.pins.outputs.dotnet_sdk_version" in workflow,
    "exact build inputs must come from canonical release pins",
)
require("persist-credentials: false" in workflow, "checkout credentials must not persist")
require(
    "python -m pip install --disable-pip-version-check -r requirements-ci.txt" in workflow,
    "CI Python dependencies must install from the pinned requirements file",
)
require(requirements.is_file(), "requirements-ci.txt must exist")
req = requirements.read_text(encoding="utf-8")
require(
    re.search(r"(?m)^playwright==1\.63\.0$", req) is not None,
    "Playwright must be pinned to 1.63.0",
)
require(dependabot.is_file(), ".github/dependabot.yml must exist")
dep = dependabot.read_text(encoding="utf-8")
require('package-ecosystem: "github-actions"' in dep, "Dependabot must track GitHub Actions")
require('package-ecosystem: "pip"' in dep, "Dependabot must track Python CI dependencies")

print("CI SUPPLY-CHAIN CONTRACT: PASS")
