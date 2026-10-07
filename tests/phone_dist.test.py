from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "phone" / "make-phone-dist.py"
PINS = ROOT / "release" / "pins.env"


def pins() -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in PINS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        result[key] = value
    return result


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_bundle(path: Path) -> None:
    members = {
        "ArchiSteamFarm": b"runtime\n",
        "plugins/AccountManager/AccountManager.dll": b"account\n",
        "plugins/ControlCenter/ControlCenter.dll": b"center\n",
        "plugins/ControlWeb/ControlWeb.dll": b"web\n",
        "plugins/PlaytimeGoals/PlaytimeGoals.dll": b"ptg\n",
        "plugins/ControlWeb/www/index.html": b"<html></html>\n",
        "plugins/ControlWeb/www/i18n.js": b"i18n\n",
        "plugins/ControlWeb/www/core.js": b"core\n",
        "plugins/ControlWeb/www/qrcode.min.js": b"qr\n",
        "plugins/ControlWeb/www/qrcode.LICENSE.txt": b"license\n",
        "plugins/ControlWeb/www/app.js": b"app\n",
        "plugins/ControlWeb/www/app.css": b"css\n",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(members.items()):
            info = zipfile.ZipInfo(name)
            info.external_attr = ((0o100755 if name == "ArchiSteamFarm" else 0o100644) << 16)
            archive.writestr(info, payload)


def create_release_fixture(artifacts: Path, p: dict[str, str]) -> Path:
    artifacts.mkdir()
    bundle = artifacts / f"ASF-Control-Suite-v{p['CONTROL_SUITE_VERSION']}.zip"
    create_bundle(bundle)
    metadata = {
        "schemaVersion": 1,
        "release": {
            "controlModuleVersion": p["CONTROL_MODULE_VERSION"],
            "controlSuiteVersion": p["CONTROL_SUITE_VERSION"],
            "playtimeGoalsVersion": p["PLAYTIMEGOALS_VERSION"],
        },
        "targets": {
            "asfCommit": p["ASF_COMMIT"],
            "asfPatchSha256": p["ASF_PATCH_SHA256"],
            "asfUiCommit": p["ASF_UI_COMMIT"],
            "asfVersion": p["ASF_VERSION"],
            "dotnetSdkVersion": p["DOTNET_SDK_VERSION"],
            "playtimeGoalsCommit": p["PLAYTIMEGOALS_COMMIT"],
        },
        "install": {
            "canonicalControlPath": "/Control/",
            "extractInto": "<ASF>/",
            "webPath": "/",
        },
        "artifacts": [bundle.name],
    }
    meta_path = artifacts / "CONTROL-SUITE-METADATA.json"
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (artifacts / "SHA256SUMS").write_text(
        f"{sha(bundle)}  {bundle.name}\n{sha(meta_path)}  {meta_path.name}\n",
        encoding="utf-8",
    )
    return bundle


def run_builder(artifacts: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--artifacts",
            str(artifacts),
            "--out",
            str(output),
            "--suite-root",
            str(ROOT),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


p = pins()
with tempfile.TemporaryDirectory() as td:
    temp = Path(td)
    artifacts = temp / "artifacts"
    bundle = create_release_fixture(artifacts, p)
    first = temp / "first.tar.gz"
    second = temp / "second.tar.gz"

    one = run_builder(artifacts, first)
    if one.returncode != 0:
        raise AssertionError(one.stdout + one.stderr)

    two = run_builder(artifacts, second)
    if two.returncode != 0:
        raise AssertionError(two.stdout + two.stderr)

    assert first.read_bytes() == second.read_bytes(), "phone archive must be deterministic"

    with tarfile.open(first, "r:gz") as archive:
        names = set(archive.getnames())
        root = "asf-control-suite-v1.0-dist"
        required = {
            root,
            f"{root}/ArchiSteamFarm",
            f"{root}/BUILD-METADATA.txt",
            f"{root}/INSTALL-LAYOUT.txt",
            f"{root}/SHA256SUMS",
            f"{root}/installer/phone-transaction.sh",
            f"{root}/installer/phone-rollback-core.sh",
            f"{root}/plugins/PlaytimeGoals/PlaytimeGoals.dll",
            f"{root}/plugins/ControlWeb/www/index.html",
        }
        assert required <= names
        runtime = archive.getmember(f"{root}/ArchiSteamFarm")
        transaction = archive.getmember(f"{root}/installer/phone-transaction.sh")
        assert runtime.mode & 0o111
        assert transaction.mode & 0o111

        build_metadata = archive.extractfile(f"{root}/BUILD-METADATA.txt").read().decode()
        assert f"ASF commit: {p['ASF_COMMIT']}" in build_metadata
        assert f"PlaytimeGoals commit: {p['PLAYTIMEGOALS_COMMIT']}" in build_metadata
        assert "Control Suite commit:" in build_metadata

        checksum_text = archive.extractfile(f"{root}/SHA256SUMS").read().decode()
        assert "  ArchiSteamFarm\n" in checksum_text
        assert "  installer/phone-transaction.sh\n" in checksum_text

    bundle.write_bytes(bundle.read_bytes() + b"tamper")
    bad = run_builder(artifacts, temp / "bad.tar.gz")
    assert bad.returncode != 0
    assert "bundle SHA256 mismatch" in bad.stdout + bad.stderr

print("PHONE DIST CONTRACT: PASS")
