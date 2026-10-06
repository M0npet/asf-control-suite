from pathlib import Path
import hashlib
import io
import shutil
import tarfile
import os
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]

PINS = ROOT / "release" / "pins.env"
MANIFEST = ROOT / "release" / "dotnet-sdk.sha512"
CHECKER = ROOT / "scripts" / "build" / "check-dotnet.sh"
BOOTSTRAP = ROOT / "scripts" / "dev" / "bootstrap-dotnet-sdk.sh"
MAKE_RELEASE = ROOT / "scripts" / "build" / "make-release.sh"

EXPECTED_HASHES = {
    "linux-x64": (
        "1033977dd837150e0814cf0c5d5b17ceb63925fda7ba2158b47258a4bd7c048c"
        "f82eac3bc1166f3146f53124a3f5fba09db1de1260d2ce96399860303b404b48"
    ),
    "linux-arm64": (
        "a1b45da58e5591fff909a6126ac6bfc1ef9c12bc72c0625f7815e83a82be1a9"
        "02317ee96926cbbf81324a45c6abf2ed8102a216d0507879cc166159af78d1b77"
    ),
}

errors = []


def parse_pins(path: Path) -> dict[str, str]:
    result = {}

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            raise RuntimeError(
                f"malformed pin line: {raw!r}"
            )

        key, value = line.split("=", 1)
        result[key] = value

    return result


pins = parse_pins(PINS)
sdk_version = pins.get("DOTNET_SDK_VERSION", "")

if not re.fullmatch(
    r"\d+\.\d+\.\d+",
    sdk_version,
):
    errors.append(
        "DOTNET_SDK_VERSION is missing or malformed"
    )


# ------------------------------------------------------------------
# Release builder: strictly offline with respect to SDK acquisition.
# ------------------------------------------------------------------

if not MAKE_RELEASE.is_file():
    errors.append(
        "make-release.sh missing"
    )
else:
    make_text = MAKE_RELEASE.read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "dotnet-install.sh",
        "https://dot.net/",
        "curl ",
        "wget ",
    ):
        if forbidden in make_text:
            errors.append(
                f"make-release.sh still contains forbidden SDK bootstrap construct: {forbidden}"
            )

    if "check-dotnet.sh" not in make_text:
        errors.append(
            "make-release.sh does not invoke fail-closed exact SDK gate"
        )


# ------------------------------------------------------------------
# Checked-in integrity manifest for the exact pinned SDK assets.
# Version remains canonical only in release/pins.env.
# ------------------------------------------------------------------

if not MANIFEST.is_file():
    errors.append(
        "release/dotnet-sdk.sha512 missing"
    )
else:
    hashes = {}

    for raw in MANIFEST.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            errors.append(
                f"malformed SDK hash manifest line: {raw!r}"
            )
            continue

        rid, value = line.split("=", 1)

        if rid in hashes:
            errors.append(
                f"duplicate SDK hash RID: {rid}"
            )
            continue

        hashes[rid] = value

    if set(hashes) != set(EXPECTED_HASHES):
        errors.append(
            "SDK hash manifest must contain exactly linux-x64 and linux-arm64"
        )

    for rid, expected in EXPECTED_HASHES.items():
        actual = hashes.get(rid, "")

        if not re.fullmatch(
            r"[0-9a-f]{128}",
            actual,
        ):
            errors.append(
                f"invalid SHA-512 for {rid}"
            )
            continue

        if actual != expected:
            errors.append(
                f"unexpected official SHA-512 for {rid}"
            )


# ------------------------------------------------------------------
# Exact installed SDK gate.
# ------------------------------------------------------------------

if not CHECKER.is_file():
    errors.append(
        "scripts/build/check-dotnet.sh missing"
    )
else:
    checker_text = CHECKER.read_text(
        encoding="utf-8"
    )

    for required in (
        "pins.sh",
        "load_release_pins",
        "DOTNET_SDK_VERSION",
        "--list-sdks",
    ):
        if required not in checker_text:
            errors.append(
                f"check-dotnet.sh missing: {required}"
            )

    for forbidden in (
        "dotnet-install.sh",
        "curl ",
        "wget ",
        "10.0.400",
    ):
        if forbidden in checker_text:
            errors.append(
                f"check-dotnet.sh contains forbidden hardcoded/bootstrap value: {forbidden}"
            )

    # Verify exact SDK succeeds, wrong SDK fails, and empty SDK list fails.
    with tempfile.TemporaryDirectory() as td:
        fake_dir = Path(td)
        fake_dotnet = fake_dir / "dotnet"

        def run_fake(list_output: str):
            fake_dotnet.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"${1:-}\" == \"--list-sdks\" ]]; then\n"
                f"  printf '%s\\n' {list_output!r}\n"
                "  exit 0\n"
                "fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            fake_dotnet.chmod(0o755)

            env = dict(os.environ)
            env.pop("CONTROL_DOTNET", None)
            env.pop("DOTNET_ROOT", None)
            env["PATH"] = (
                str(fake_dir)
                + ":/usr/local/sbin:/usr/local/bin:/usr/bin:/bin"
            )

            return subprocess.run(
                ["/usr/bin/bash", str(CHECKER)],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

        exact = run_fake(
            f"{sdk_version} [/fake/sdk]"
        )

        if exact.returncode != 0:
            errors.append(
                "exact pinned SDK is rejected by check-dotnet.sh"
            )

        wrong = run_fake(
            "10.0.401 [/fake/sdk]"
        )

        if wrong.returncode == 0:
            errors.append(
                "wrong SDK unexpectedly passes check-dotnet.sh"
            )

        missing = run_fake("")

        if missing.returncode == 0:
            errors.append(
                "missing exact SDK unexpectedly passes check-dotnet.sh"
            )


# ------------------------------------------------------------------
# Explicit developer bootstrap.
# It may download an SDK archive, but must verify the repo-pinned
# SHA-512 before any extraction and must never execute remote scripts.
# ------------------------------------------------------------------

if not BOOTSTRAP.is_file():
    errors.append(
        "scripts/dev/bootstrap-dotnet-sdk.sh missing"
    )
else:
    bootstrap_text = BOOTSTRAP.read_text(
        encoding="utf-8"
    )

    for required in (
        "DOTNET_SDK_VERSION",
        "dotnet-sdk.sha512",
        "builds.dotnet.microsoft.com",
        "sha512",
        "tar ",
        "--verify-only",
        "--archive",
        "--rid",
    ):
        if required not in bootstrap_text:
            errors.append(
                f"bootstrap-dotnet-sdk.sh missing: {required}"
            )

    for forbidden in (
        "dotnet-install.sh",
        "https://dot.net/v1/",
        "| bash",
        "| sh",
    ):
        if forbidden in bootstrap_text:
            errors.append(
                f"bootstrap contains forbidden remote-script execution construct: {forbidden}"
            )

    verify_pos = bootstrap_text.find("sha512")
    extract_pos = bootstrap_text.find("tar ")

    if (
        verify_pos < 0
        or extract_pos < 0
        or verify_pos > extract_pos
    ):
        errors.append(
            "bootstrap does not visibly verify SHA-512 before extraction"
        )

    # Corrupt local archive must fail before extraction.
    with tempfile.TemporaryDirectory() as td:
        bad_archive = Path(td) / (
            f"dotnet-sdk-{sdk_version}-linux-x64.tar.gz"
        )

        bad_archive.write_bytes(
            b"intentionally-corrupted-sdk-archive"
        )

        result = subprocess.run(
            [
                "/usr/bin/bash",
                str(BOOTSTRAP),
                "--archive",
                str(bad_archive),
                "--rid",
                "linux-x64",
                "--verify-only",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            errors.append(
                "corrupted SDK archive unexpectedly passed verification"
            )


# User-supplied existing install directories must fail closed.
#
# A typo in --install-dir must never turn the bootstrap into a
# recursive directory deletion primitive. Existing custom directories
# are allowed only when they already contain the exact SDK and the
# bootstrap can return without modifying them.
with tempfile.TemporaryDirectory() as td:
    temp_root = Path(td)
    fake_suite = temp_root / "suite"

    (fake_suite / "scripts" / "dev").mkdir(parents=True)
    (fake_suite / "scripts" / "build").mkdir(parents=True)
    (fake_suite / "release").mkdir(parents=True)

    shutil.copy2(
        BOOTSTRAP,
        fake_suite / "scripts" / "dev" / BOOTSTRAP.name,
    )
    shutil.copy2(
        ROOT / "scripts" / "build" / "pins.sh",
        fake_suite / "scripts" / "build" / "pins.sh",
    )
    shutil.copy2(
        PINS,
        fake_suite / "release" / "pins.env",
    )

    fake_archive = temp_root / (
        f"dotnet-sdk-{sdk_version}-linux-x64.tar.gz"
    )

    fake_dotnet = (
        "#!/usr/bin/env bash\n"
        "if [[ \"${1:-}\" == \"--list-sdks\" ]]; then\n"
        f"    echo \"{sdk_version} [/fake/sdk]\"\n"
        "    exit 0\n"
        "fi\n"
        "exit 0\n"
    ).encode("utf-8")

    with tarfile.open(
        fake_archive,
        mode="w:gz",
    ) as archive:
        info = tarfile.TarInfo("dotnet")
        info.mode = 0o755
        info.size = len(fake_dotnet)

        archive.addfile(
            info,
            io.BytesIO(fake_dotnet),
        )

    fake_hash = hashlib.sha512(
        fake_archive.read_bytes()
    ).hexdigest()

    (
        fake_suite / "release" / "dotnet-sdk.sha512"
    ).write_text(
        f"linux-x64={fake_hash}\n",
        encoding="utf-8",
    )

    custom_install = temp_root / "important-user-directory"
    custom_install.mkdir()

    sentinel = custom_install / "DO-NOT-DELETE.txt"
    sentinel.write_text(
        "unrelated user data\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "/usr/bin/bash",
            str(
                fake_suite
                / "scripts"
                / "dev"
                / "bootstrap-dotnet-sdk.sh"
            ),
            "--archive",
            str(fake_archive),
            "--rid",
            "linux-x64",
            "--install-dir",
            str(custom_install),
        ],
        cwd=fake_suite,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        errors.append(
            "user-supplied existing install directory was "
            "silently replaced instead of failing closed"
        )

    if not sentinel.is_file():
        errors.append(
            "user-supplied existing install directory lost "
            "pre-existing data"
        )


if errors:
    print("DOTNET SUPPLY-CHAIN CONTRACT: FAIL")

    for error in errors:
        print(" -", error)

    raise SystemExit(1)

print("DOTNET SUPPLY-CHAIN CONTRACT: PASS")
