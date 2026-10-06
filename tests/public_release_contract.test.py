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
# Phase 10 scope:
# public source/documentation readiness only.
#
# CI, tags, GitHub Releases and publication automation belong
# to the later GitHub publication phase after security + live
# field verification.
# ------------------------------------------------------------

for relative in (
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "docs/installation/manual.md",
    "docs/architecture/README.md",
    "docs/development/README.md",
):
    read(relative)


# README must describe the actual current release.
for token, reason in (
    (
        "ASF Control Suite v1.0.0",
        "current release branding",
    ),
    (
        "PlaytimeGoals 0.5.1.0",
        "current PlaytimeGoals version",
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
        "ASF-Control-Suite-v1.0.0.zip",
        "native bundle artifact",
    ),
    (
        "<ASF>/plugins/",
        "native ASF extraction target",
    ),
    (
        "page memory",
        "RAM-only IPC password model",
    ),
):
    require(
        "README.md",
        token,
        reason,
    )


# Installation documentation must describe the real current
# release pipeline and native ZIP layout.
manual = "docs/installation/manual.md"

for token, reason in (
    (
        "scripts/build/make-release.sh",
        "current release builder",
    ),
    (
        "ASF-Control-Suite-v1.0.0.zip",
        "bundle ZIP",
    ),
    (
        "AccountManager-v1.0.0.zip",
        "AccountManager ZIP",
    ),
    (
        "ControlCenter-v1.0.0.zip",
        "ControlCenter ZIP",
    ),
    (
        "ControlWeb-v1.0.0.zip",
        "ControlWeb ZIP",
    ),
    (
        "PlaytimeGoals-v0.5.1.zip",
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
        "<ASF>/plugins/",
        "native extraction target",
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
