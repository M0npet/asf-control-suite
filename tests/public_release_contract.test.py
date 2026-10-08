from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def read(relative: str) -> str:
    path = ROOT / relative

    if not path.is_file():
        errors.append(
            f"required public file missing: {relative}"
        )
        return ""

    return path.read_text(
        encoding="utf-8"
    )


def require(
    relative: str,
    token: str,
    reason: str,
) -> None:
    text = read(relative)

    if token not in text:
        errors.append(
            f"{relative}: missing {reason}: {token!r}"
        )


# ------------------------------------------------------------
# Public source/documentation release contract.
#
# v1.0.0 has passed final live verification and is published.
# main may target a newer candidate, but public docs must keep
# stable provenance explicit while current build artifact names
# are derived from release/pins.env.
# ------------------------------------------------------------

for relative in (
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "docs/installation/manual.md",
    "docs/architecture/README.md",
    "docs/development/README.md",
    ".github/workflows/publish-release.yml",
):
    read(relative)

for token, reason in (
    ("workflow_dispatch:", "manual publication gate"),
    ("accepted_phone_sha256:", "live-accepted candidate checksum input"),
    ("CONTROL-SUITE-COMMIT.txt", "exact source provenance check"),
    ("sha256sum -c SHA256SUMS", "artifact checksum verification"),
    ("asf-control-suite-$TARGET_SHA", "artifact name bound to exact source commit"),
    ("jq -r .expired", "expired artifact rejection"),
    ("git/ref/tags/$RELEASE_TAG", "pre-existing tag reuse guard"),
    ("cancel-in-progress: false", "release publication serialization"),
    ("Live-accepted phone SHA-256", "release-note provenance record"),
    ("refusing to mutate it", "existing-release mutation guard"),
):
    require(
        ".github/workflows/publish-release.yml",
        token,
        reason,
    )

require(
    ".github/workflows/ci.yml",
    "retention-days: 30",
    "live-acceptance artifact retention",
)


# README must describe both the published stable state and the current main candidate.
for token, reason in (
    (
        "releases/tag/v1.0.0",
        "published v1.0.0 release link",
    ),
    (
        "| PlaytimeGoals | **0.5.3.0** |",
        "current PlaytimeGoals compatibility version",
    ),
    (
        "v1.1.0 candidate",
        "current unreleased candidate identity",
    ),
    (
        "release/pins.env",
        "canonical release pins",
    ),
    (
        "docs/installation/manual.md",
        "current installation documentation",
    ),
    (
        "page memory",
        "RAM-only IPC password model",
    ),
    (
        "15314163bfccd26207fe9c1e3a8504727fea2910",
        "published v1.0.0 provenance commit",
    ),
):
    require(
        "README.md",
        token,
        reason,
    )



# README pinned revisions must reflect canonical release/pins.env values.
pins = {}

for raw in (ROOT / "release" / "pins.env").read_text(
    encoding="utf-8"
).splitlines():
    line = raw.strip()

    if (
        not line
        or line.startswith("#")
        or "=" not in line
    ):
        continue

    key, value = line.split("=", 1)
    pins[key] = value

for key, label in (
    ("ASF_COMMIT", "ASF"),
    ("ASF_PATCH_SHA256", "ASF compatibility patch"),
    ("ASF_UI_COMMIT", "ASF-ui"),
    ("PLAYTIMEGOALS_COMMIT", "PlaytimeGoals"),
):
    value = pins.get(key, "")

    if not value:
        errors.append(
            f"release/pins.env missing {key}"
        )
        continue

    require(
        "README.md",
        value,
        f"{label} pinned revision",
    )

# Installation documentation must describe the real current
# release pipeline and native ZIP layout.
manual = "docs/installation/manual.md"

suite_version = pins.get("CONTROL_SUITE_VERSION", "")
playtime_version = pins.get("PLAYTIMEGOALS_VERSION", "").removesuffix(".0")

for token, reason in (
    (
        "scripts/build/make-release.sh",
        "current release builder",
    ),
    (
        f"ASF-Control-Suite-v{suite_version}.zip",
        "bundle ZIP",
    ),
    (
        f"AccountManager-v{suite_version}.zip",
        "AccountManager ZIP",
    ),
    (
        f"ControlCenter-v{suite_version}.zip",
        "ControlCenter ZIP",
    ),
    (
        f"ControlWeb-v{suite_version}.zip",
        "ControlWeb ZIP",
    ),
    (
        f"PlaytimeGoals-v{playtime_version}.zip",
        "PlaytimeGoals ZIP",
    ),
    (
        "CONTROL-SUITE-METADATA.json",
        "release metadata",
    ),
    (
        "SHA256SUMS",
        "release checksums",
    ),
    (
        "<ASF>/",
        "suite extraction target",
    ),
    (
        "CONTROL_DOTNET",
        "exact SDK override",
    ),
):
    require(
        manual,
        token,
        reason,
    )


# Architecture/development docs must be real docs, not the
# migration placeholders currently in the tree.
for relative in (
    "docs/architecture/README.md",
    "docs/development/README.md",
):
    text = read(relative)

    if text and len(text.strip()) < 500:
        errors.append(
            f"{relative}: still only a placeholder"
        )

    if (
        "will be finalized before v1.0.0"
        in text
    ):
        errors.append(
            f"{relative}: pre-release placeholder remains"
        )


# Search every public Markdown document for claims already
# invalidated by completed phases.
markdown = sorted(
    path
    for path in ROOT.rglob("*.md")
    if ".git" not in path.parts
    and ".venv" not in path.parts
    and "artifacts" not in path.parts
)

stale_literals = (
    "PlaytimeGoals 0.5.0.0",
    "fa959d3d4ffd09f7fd30e9ee8599aa5004b67033",
    "asf-control-suite-v1.0-dist.tar.gz",
    "docs/INSTALL.md",
    "scripts/make-release.sh",
    "cannot download SDK 10.0.400",
    "dotnet is not installed",
)

stale_ipc = re.compile(
    r"(?:IPCPassword|IPC password).{0,180}sessionStorage",
    re.IGNORECASE | re.DOTALL,
)

for path in markdown:
    text = path.read_text(
        encoding="utf-8"
    )

    relative = path.relative_to(
        ROOT
    ).as_posix()

    for token in stale_literals:
        if token in text:
            errors.append(
                f"{relative}: stale public claim: {token}"
            )

    if stale_ipc.search(text):
        errors.append(
            f"{relative}: stale IPC/sessionStorage claim"
        )


if errors:
    print(
        "PUBLIC DOCUMENTATION CONTRACT: FAIL"
    )

    for error in errors:
        print(
            " -",
            error,
        )

    raise SystemExit(1)

print(
    "PUBLIC DOCUMENTATION CONTRACT: PASS"
)
