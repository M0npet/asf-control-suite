from __future__ import annotations

import ipaddress
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = "tests/privacy_contract.test.py"
errors: list[str] = []

TEXT_SUFFIXES = {
    ".md", ".txt", ".yml", ".yaml", ".json",
    ".env", ".py", ".js", ".css", ".html",
    ".sh", ".cs", ".csproj", ".xml", ".toml",
    ".ini", ".cfg", ".conf", ".props", ".targets",
}

TEXT_NAMES = {
    ".gitignore",
    "LICENSE",
    "NOTICE",
}

EMAIL = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)

LOCAL_HOME = re.compile(
    r"(?:/home/|/Users/|[A-Za-z]:\\Users\\)"
    r"[^\s\"'`<>]+"
)

STEAM_ID64 = re.compile(
    r"\b7656\d{13}\b"
)

TOKEN = re.compile(
    r"\b(?:"
    r"gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-[A-Za-z0-9_-]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r")\b"
)

PRIVATE_KEY = re.compile(
    r"-----BEGIN "
    r"(?:RSA |EC |OPENSSH )?"
    r"PRIVATE KEY-----"
)

STEAM_COOKIE = re.compile(
    r"(?:steamLoginSecure|sessionid)"
    r"\s*[:=]\s*"
    r"[\"']?[A-Za-z0-9%._-]{10,}",
    re.IGNORECASE,
)

IPV4 = re.compile(
    r"(?<!\d)"
    r"(?:\d{1,3}\.){3}\d{1,3}"
    r"(?!\d)"
)


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
    )

    return [
        ROOT / value.decode("utf-8")
        for value in raw.split(b"\0")
        if value
    ]


for path in tracked_files():
    if not path.is_file():
        continue

    relative = path.relative_to(ROOT).as_posix()

    if relative == SELF:
        continue

    if (
        path.name not in TEXT_NAMES
        and path.suffix.lower() not in TEXT_SUFFIXES
    ):
        continue

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    for match in EMAIL.finditer(text):
        errors.append(
            f"{relative}: e-mail: {match.group(0)!r}"
        )

    for match in LOCAL_HOME.finditer(text):
        errors.append(
            f"{relative}: local path: {match.group(0)!r}"
        )

    for match in STEAM_ID64.finditer(text):
        errors.append(
            f"{relative}: SteamID64: {match.group(0)!r}"
        )

    if TOKEN.search(text):
        errors.append(
            f"{relative}: token-like secret"
        )

    if PRIVATE_KEY.search(text):
        errors.append(
            f"{relative}: private key material"
        )

    if STEAM_COOKIE.search(text):
        errors.append(
            f"{relative}: Steam cookie-like secret"
        )

    for match in IPV4.finditer(text):
        raw = match.group(0)

        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            continue

        cgnat = address in ipaddress.ip_network(
            "100.64.0.0/10"
        )

        if address.is_private or cgnat:
            errors.append(
                f"{relative}: private/CGNAT IPv4: {raw!r}"
            )


history = subprocess.check_output(
    ["git", "log", "--all", "--format=%ae%n%ce"],
    cwd=ROOT,
    text=True,
)

for email in (
    line.strip()
    for line in history.splitlines()
):
    if not email:
        continue

    if email == "noreply@github.com":
        continue

    if email.endswith(
        "@users.noreply.github.com"
    ):
        continue

    errors.append(
        "git history: non-noreply e-mail: "
        f"{email!r}"
    )


if errors:
    print("PRIVACY CONTRACT: FAIL")

    for error in errors:
        print(" -", error)

    raise SystemExit(1)


print("PRIVACY CONTRACT: PASS")
