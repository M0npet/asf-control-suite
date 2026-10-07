#!/usr/bin/env python3

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


DIST_NAME = "asf-control-suite-v1.0-dist"
REQUIRED_WEB_ASSETS = (
    "app.css",
    "app.js",
    "core.js",
    "i18n.js",
    "index.html",
    "qrcode.LICENSE.txt",
    "qrcode.min.js",
)
PLUGINS = (
    "AccountManager",
    "ControlCenter",
    "ControlWeb",
    "PlaytimeGoals",
)


def die(message: str) -> "NoReturn":
    raise SystemExit(f"PHONE DIST: FAIL: {message}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_pins(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            die(f"malformed pin line {number}")
        key, value = line.split("=", 1)
        if not key or not value or key in result:
            die(f"invalid pin line {number}")
        result[key] = value

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
    missing = [key for key in required if key not in result]
    if missing:
        die("missing pins: " + ", ".join(missing))
    return result


def parse_checksums(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = raw.split("  ", 1)
        if (
            len(parts) != 2
            or len(parts[0]) != 64
            or any(ch not in "0123456789abcdef" for ch in parts[0])
            or "/" in parts[1]
            or "\\" in parts[1]
        ):
            die(f"malformed release checksum line {number}")
        digest, name = parts
        if name in rows:
            die(f"duplicate release checksum entry: {name}")
        rows[name] = digest
    return rows


def validate_release_metadata(path: Path, pins: dict[str, str]) -> None:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        die(f"invalid release metadata: {exc}")

    expected = {
        "controlSuiteVersion": pins["CONTROL_SUITE_VERSION"],
        "controlModuleVersion": pins["CONTROL_MODULE_VERSION"],
        "playtimeGoalsVersion": pins["PLAYTIMEGOALS_VERSION"],
    }
    if metadata.get("release") != expected:
        die("release metadata versions do not match canonical pins")

    targets = metadata.get("targets")
    if not isinstance(targets, dict):
        die("release metadata targets missing")

    expected_targets = {
        "asfVersion": pins["ASF_VERSION"],
        "asfCommit": pins["ASF_COMMIT"],
        "asfPatchSha256": pins["ASF_PATCH_SHA256"],
        "asfUiCommit": pins["ASF_UI_COMMIT"],
        "playtimeGoalsCommit": pins["PLAYTIMEGOALS_COMMIT"],
        "dotnetSdkVersion": pins["DOTNET_SDK_VERSION"],
    }
    if targets != expected_targets:
        die("release metadata targets do not match canonical pins")

    install = metadata.get("install")
    if install != {
        "extractInto": "<ASF>/",
        "webPath": "/",
        "canonicalControlPath": "/Control/",
    }:
        die("release metadata install layout is not the default-root layout")


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or len(value) != 40:
        die("cannot resolve Control Suite source commit")
    return value


def safe_bundle_member(name: str) -> PurePosixPath:
    if "\\" in name:
        die(f"unsafe bundle member: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        die(f"unsafe bundle member: {name!r}")
    if name != "ArchiSteamFarm" and path.parts[0] != "plugins":
        die(f"unexpected bundle member: {name!r}")
    return path


def extract_bundle(bundle: Path, dist: Path) -> None:
    expected_files = {
        "ArchiSteamFarm",
        *(f"plugins/{plugin}/{plugin}.dll" for plugin in PLUGINS),
        *(f"plugins/ControlWeb/www/{asset}" for asset in REQUIRED_WEB_ASSETS),
    }

    seen: set[str] = set()
    try:
        with zipfile.ZipFile(bundle, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                die(f"bundle CRC failure: {bad}")

            for info in archive.infolist():
                if info.is_dir():
                    die("directory entries are forbidden in canonical bundle")
                path = safe_bundle_member(info.filename)
                relative = path.as_posix()
                if relative in seen:
                    die(f"duplicate bundle member: {relative}")
                seen.add(relative)

                mode = info.external_attr >> 16
                kind = mode & 0o170000
                if kind not in (0, 0o100000):
                    die(f"non-regular bundle member: {relative}")

                target = dist.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
                target.chmod(0o755 if relative == "ArchiSteamFarm" else 0o644)
    except zipfile.BadZipFile as exc:
        die(f"invalid bundle ZIP: {exc}")

    if seen != expected_files:
        missing = sorted(expected_files - seen)
        extra = sorted(seen - expected_files)
        die(f"bundle layout mismatch; missing={missing!r}; extra={extra!r}")


def write_metadata(dist: Path, suite_root: Path, pins: dict[str, str]) -> None:
    suite_commit = git_head(suite_root)
    build_metadata = "\n".join(
        (
            f"Control Suite version: {pins['CONTROL_SUITE_VERSION']}",
            f"Control Suite commit: {suite_commit}",
            f"Control module version: {pins['CONTROL_MODULE_VERSION']}",
            f"ASF version: {pins['ASF_VERSION']}",
            f"ASF commit: {pins['ASF_COMMIT']}",
            f"ASF patch SHA256: {pins['ASF_PATCH_SHA256']}",
            f"ASF-ui commit: {pins['ASF_UI_COMMIT']}",
            f"PlaytimeGoals version: {pins['PLAYTIMEGOALS_VERSION']}",
            f"PlaytimeGoals commit: {pins['PLAYTIMEGOALS_COMMIT']}",
            f".NET SDK version: {pins['DOTNET_SDK_VERSION']}",
            "",
        )
    )
    (dist / "BUILD-METADATA.txt").write_text(build_metadata, encoding="utf-8")

    layout = """ASF Control Suite phone distribution

ArchiSteamFarm -> /opt/asf/ArchiSteamFarm
plugins/AccountManager -> /opt/asf/plugins/AccountManager
plugins/ControlCenter -> /opt/asf/plugins/ControlCenter
plugins/ControlWeb -> /opt/asf/plugins/ControlWeb
plugins/PlaytimeGoals -> /opt/asf/plugins/PlaytimeGoals

installer/phone-transaction.sh is executed from the temporary distribution.
The existing ASF config, bot databases and credentials are not packaged.
The installer transactionally backs up the previous runtime, plugins,
ASF.json and the stock ASF-ui root entrypoint before swapping bytes.
"""
    (dist / "INSTALL-LAYOUT.txt").write_text(layout, encoding="utf-8")


def copy_installers(dist: Path, suite_root: Path) -> None:
    target = dist / "installer"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("phone-transaction.sh", "phone-rollback-core.sh"):
        source = suite_root / "installer" / name
        if not source.is_file():
            die(f"installer source missing: {source}")
        destination = target / name
        shutil.copyfile(source, destination)
        destination.chmod(0o755)


def write_internal_checksums(dist: Path) -> None:
    rows: list[str] = []
    for path in sorted(p for p in dist.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        relative = path.relative_to(dist).as_posix()
        rows.append(f"{sha256_file(path)}  {relative}\n")
    (dist / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")


def add_tar_entry(archive: tarfile.TarFile, root: Path, path: Path) -> None:
    relative = path.relative_to(root.parent).as_posix()
    info = tarfile.TarInfo(relative)
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0

    if path.is_dir():
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.size = 0
        archive.addfile(info)
        return

    info.type = tarfile.REGTYPE
    info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
    data = path.read_bytes()
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def create_deterministic_tar(dist: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                add_tar_entry(archive, dist, dist)
                for path in sorted(dist.rglob("*"), key=lambda item: item.relative_to(dist).as_posix()):
                    if path.is_symlink() or not (path.is_file() or path.is_dir()):
                        die(f"unsupported distribution node: {path}")
                    add_tar_entry(archive, dist, path)
    os.replace(temporary, output)


def verify_tar(output: Path) -> None:
    try:
        with tarfile.open(output, "r:gz") as archive:
            names = archive.getnames()
            if not names or names[0] != DIST_NAME:
                die("phone archive root is invalid")
            for member in archive.getmembers():
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts or name.parts[0] != DIST_NAME:
                    die(f"unsafe phone archive member: {member.name!r}")
                if not (member.isdir() or member.isfile()):
                    die(f"unsupported phone archive member: {member.name!r}")
    except tarfile.TarError as exc:
        die(f"invalid phone archive: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Mi Max 2 phone distribution from a verified native release.")
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--suite-root", type=Path)
    args = parser.parse_args()

    suite_root = (args.suite_root or Path(__file__).resolve().parents[2]).resolve()
    artifacts = args.artifacts.resolve()
    output = args.out.resolve()
    pins = parse_pins(suite_root / "release" / "pins.env")

    metadata = artifacts / "CONTROL-SUITE-METADATA.json"
    manifest = artifacts / "SHA256SUMS"
    bundle = artifacts / f"ASF-Control-Suite-v{pins['CONTROL_SUITE_VERSION']}.zip"
    for required in (metadata, manifest, bundle):
        if not required.is_file():
            die(f"release artifact missing: {required}")

    validate_release_metadata(metadata, pins)
    release_checksums = parse_checksums(manifest)
    expected_bundle_sha = release_checksums.get(bundle.name)
    if expected_bundle_sha is None:
        die("bundle is not covered by release SHA256SUMS")
    actual_bundle_sha = sha256_file(bundle)
    if actual_bundle_sha != expected_bundle_sha:
        die(f"bundle SHA256 mismatch: expected {expected_bundle_sha}, got {actual_bundle_sha}")

    with tempfile.TemporaryDirectory(prefix="asf-control-phone-") as tmp:
        dist = Path(tmp) / DIST_NAME
        dist.mkdir()
        extract_bundle(bundle, dist)
        copy_installers(dist, suite_root)
        write_metadata(dist, suite_root, pins)
        write_internal_checksums(dist)
        create_deterministic_tar(dist, output)

    verify_tar(output)
    print(f"PHONE DIST: PASS: {output}")
    print(f"PHONE DIST SHA256: {sha256_file(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
