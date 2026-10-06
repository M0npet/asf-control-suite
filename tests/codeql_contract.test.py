from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = ROOT / ".github/workflows/codeql.yml"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


require(workflow.is_file(), ".github/workflows/codeql.yml must exist")
text = workflow.read_text(encoding="utf-8")

require("name: CodeQL" in text, "CodeQL workflow must have a stable name")
require("runs-on: ubuntu-24.04" in text, "CodeQL runner must be pinned to ubuntu-24.04")
require("languages: csharp" in text, "CodeQL must analyze C#")
require("build-mode: none" in text, "C# CodeQL must use build-mode none")
require("security-events: write" in text, "CodeQL must be allowed to upload security events")
require(
    "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in text,
    "CodeQL checkout must be pinned to checkout v7.0.1 SHA",
)
require("persist-credentials: false" in text, "CodeQL checkout credentials must not persist")
require(
    "github/codeql-action/init@2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2" in text,
    "CodeQL init must be pinned to v4.38.2 commit SHA",
)
require(
    "github/codeql-action/analyze@2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2" in text,
    "CodeQL analyze must be pinned to v4.38.2 commit SHA",
)
require("pull_request:" in text, "CodeQL must scan pull requests")
require("schedule:" in text, "CodeQL must run on a schedule")

print("CODEQL CONTRACT: PASS")
