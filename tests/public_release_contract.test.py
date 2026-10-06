from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

errors: list[str] = []


def require_file(
    relative: str,
) -> Path:
    path = ROOT / relative

    if not path.is_file():
        errors.append(
            f"required public file missing: {relative}"
        )

    return path


def read_if_present(
    relative: str,
) -> str:
    path = ROOT / relative

    if not path.is_file():
        return ""

    return path.read_text(
        encoding="utf-8",
    )


def require_text(
    relative: str,
    token: str,
    reason: str,
) -> None:
    text = read_if_present(
        relative
    )

    if token not in text:
        errors.append(
            f"{relative}: missing {reason}: {token!r}"
        )


def forbid_text(
    relative: str,
    token: str,
    reason: str,
) -> None:
    text = read_if_present(
        relative
    )

    if token in text:
        errors.append(
            f"{relative}: forbidden {reason}: {token!r}"
        )


def require_regex(
    relative: str,
    pattern: str,
    reason: str,
    flags: int = 0,
) -> None:
    text = read_if_present(
        relative
    )

    if re.search(
        pattern,
        text,
        flags,
    ) is None:
        errors.append(
            f"{relative}: missing {reason}"
        )


# ------------------------------------------------------------
# Public repository surface.
# ------------------------------------------------------------

required_files = (
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "docs/installation/manual.md",
    "docs/architecture/README.md",
    "docs/development/README.md",
    ".github/workflows/test.yml",
    ".github/workflows/security.yml",
    ".github/workflows/release.yml",
)

for relative in required_files:
    require_file(
        relative
    )


# ------------------------------------------------------------
# README contract.
# ------------------------------------------------------------

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
        "canonical pin reference",
    ),
    (
        "docs/installation/manual.md",
        "current installation documentation link",
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
    require_text(
        "README.md",
        token,
        reason,
    )


# ------------------------------------------------------------
# Installation contract.
# ------------------------------------------------------------

manual = "docs/installation/manual.md"

for token, reason in (
    (
        "scripts/build/make-release.sh",
        "current release builder path",
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
        "PlaytimeGoals standalone ZIP",
    ),
    (
        "CONTROL-SUITE-METADATA.json",
        "release metadata asset",
    ),
    (
        "SHA256SUMS",
        "release checksum asset",
    ),
    (
        "<ASF>/plugins/",
        "native extraction target",
    ),
    (
        "CONTROL_DOTNET",
        "exact SDK developer override",
    ),
):
    require_text(
        manual,
        token,
        reason,
    )


# ------------------------------------------------------------
# Placeholder public docs must be replaced.
# ------------------------------------------------------------

for relative in (
    "docs/architecture/README.md",
    "docs/development/README.md",
):
    text = read_if_present(
        relative
    )

    if (
        text
        and len(text.strip()) < 500
    ):
        errors.append(
            f"{relative}: public documentation is still only a placeholder"
        )

    if (
        "will be finalized before v1.0.0"
        in text
    ):
        errors.append(
            f"{relative}: pre-release placeholder text remains"
        )


# ------------------------------------------------------------
# Stale claims forbidden across public Markdown.
# ------------------------------------------------------------

markdown_paths = sorted(
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
    "dotnet is not installed",
    "cannot download SDK 10.0.400",
)

stale_regexes = (
    re.compile(
        r"IPCPassword.{0,160}sessionStorage",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"IPC password.{0,160}sessionStorage",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"stored only in.{0,80}sessionStorage",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"keeps? it only in sessionStorage",
        re.IGNORECASE,
    ),
)

for path in markdown_paths:
    text = path.read_text(
        encoding="utf-8",
    )

    relative = path.relative_to(
        ROOT
    ).as_posix()

    for token in stale_literals:
        if token in text:
            errors.append(
                f"{relative}: stale public claim remains: {token}"
            )

    for pattern in stale_regexes:
        if pattern.search(text):
            errors.append(
                f"{relative}: stale IPC-password/sessionStorage claim remains"
            )


# ------------------------------------------------------------
# GitHub Actions supply-chain policy.
#
# Use immutable full commit SHAs, while comments document the
# corresponding reviewed upstream release.
# ------------------------------------------------------------

CHECKOUT_RE = (
    r"uses:\s*actions/checkout@"
    r"[0-9a-f]{40}\s*#\s*v7\.0\.1"
)

DOTNET_RE = (
    r"uses:\s*actions/setup-dotnet@"
    r"[0-9a-f]{40}\s*#\s*v6\.0\.0"
)

DOTNET_VERSION_RE = (
    r"dotnet-version:\s*['\"]10\.0\.400['\"]"
)


def require_common_actions(
    workflow: str,
) -> None:
    require_regex(
        workflow,
        CHECKOUT_RE,
        "checkout pinned to full SHA for v7.0.1",
    )

    require_regex(
        workflow,
        DOTNET_RE,
        "setup-dotnet pinned to full SHA for v6.0.0",
    )

    require_regex(
        workflow,
        DOTNET_VERSION_RE,
        "exact .NET SDK 10.0.400",
    )


# ------------------------------------------------------------
# Test workflow.
# ------------------------------------------------------------

test_workflow = (
    ".github/workflows/test.yml"
)

require_common_actions(
    test_workflow
)

for token, reason in (
    (
        "pull_request:",
        "pull request trigger",
    ),
    (
        "push:",
        "push trigger",
    ),
    (
        "contents: read",
        "read-only repository permission",
    ),
    (
        "tests/run-all.sh",
        "canonical sandbox test suite",
    ),
    (
        "CONTROL_CHROMIUM",
        "explicit browser executable selection",
    ),
):
    require_text(
        test_workflow,
        token,
        reason,
    )


# ------------------------------------------------------------
# Security workflow.
# ------------------------------------------------------------

security_workflow = (
    ".github/workflows/security.yml"
)

require_common_actions(
    security_workflow
)

for token, reason in (
    (
        "schedule:",
        "scheduled security run",
    ),
    (
        "workflow_dispatch:",
        "manual security run",
    ),
    (
        "contents: read",
        "read-only repository permission",
    ),
    (
        "tests/static_contracts.py",
        "security/static contract execution",
    ),
    (
        "tests/dotnet_supply_chain.test.py",
        "SDK supply-chain contract execution",
    ),
):
    require_text(
        security_workflow,
        token,
        reason,
    )


# ------------------------------------------------------------
# Release workflow.
# ------------------------------------------------------------

release_workflow = (
    ".github/workflows/release.yml"
)

require_common_actions(
    release_workflow
)

for token, reason in (
    (
        "workflow_dispatch:",
        "manual release trigger",
    ),
    (
        "tags:",
        "tag release trigger",
    ),
    (
        "contents: write",
        "release publication permission",
    ),
    (
        "scripts/build/make-release.sh",
        "canonical release pipeline",
    ),
    (
        "scripts/build/verify-release-artifacts.py",
        "explicit provenance verification",
    ),
    (
        "gh release create",
        "GitHub release publication",
    ),
    (
        "ASF-Control-Suite-v",
        "bundle publication",
    ),
    (
        "AccountManager-v",
        "AccountManager publication",
    ),
    (
        "ControlCenter-v",
        "ControlCenter publication",
    ),
    (
        "ControlWeb-v",
        "ControlWeb publication",
    ),
    (
        "CONTROL-SUITE-METADATA.json",
        "metadata publication",
    ),
    (
        "SHA256SUMS",
        "checksum publication",
    ),
):
    require_text(
        release_workflow,
        token,
        reason,
    )


# Release workflow must consume the canonical builder rather than
# constructing an independent second ZIP pipeline.
for forbidden, reason in (
    (
        " zip ",
        "ad-hoc ZIP construction in release workflow",
    ),
    (
        "tar -",
        "ad-hoc archive construction in release workflow",
    ),
):
    forbid_text(
        release_workflow,
        forbidden,
        reason,
    )


# ------------------------------------------------------------
# Public release separation.
#
# Control Suite release owns bundle + Control modules.
# Standalone PlaytimeGoals remains published from its own repo.
# ------------------------------------------------------------

require_text(
    manual,
    "M0npet/PlaytimeGoals",
    "separate standalone PlaytimeGoals release ownership",
)

require_regex(
    release_workflow,
    r"Control Suite release",
    "explicit Control Suite publication set documentation",
    re.IGNORECASE,
)


if errors:
    print(
        "PUBLIC RELEASE CONTRACT: FAIL"
    )

    for error in errors:
        print(
            " -",
            error,
        )

    raise SystemExit(1)

print(
    "PUBLIC RELEASE CONTRACT: PASS"
)
