from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

VERIFY = (
    ROOT
    / "scripts"
    / "build"
    / "verify-release-artifacts.py"
)

ZIPPER = (
    ROOT
    / "scripts"
    / "build"
    / "create-native-zips.py"
)

PACKAGE = (
    ROOT
    / "scripts"
    / "build"
    / "package-release.sh"
)

PINS = (
    ROOT
    / "release"
    / "pins.env"
)

errors: list[str] = []


def parse_pins(
    path: Path,
) -> dict[str, str]:
    result: dict[str, str] = {}

    for raw in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        if "=" not in line:
            raise RuntimeError(
                f"malformed pin line: {raw!r}"
            )

        key, value = line.split(
            "=",
            1,
        )

        if key in result:
            raise RuntimeError(
                f"duplicate pin: {key}"
            )

        result[key] = value

    return result


def sha256(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


pins = parse_pins(PINS)

suite_version = pins[
    "CONTROL_SUITE_VERSION"
]

ptg_version = pins[
    "PLAYTIMEGOALS_VERSION"
]

ptg_public_version = (
    ptg_version[:-2]
    if ptg_version.endswith(".0")
    else ptg_version
)


# ------------------------------------------------------------
# Static release-pipeline enforcement.
# ------------------------------------------------------------

if not VERIFY.is_file():
    errors.append(
        "scripts/build/verify-release-artifacts.py missing"
    )

package_text = PACKAGE.read_text(
    encoding="utf-8"
)

if "verify-release-artifacts.py" not in package_text:
    errors.append(
        "package-release.sh does not invoke release provenance verifier"
    )

if package_text.count(
    "verify-release-artifacts.py"
) != 1:
    errors.append(
        "package-release.sh must invoke release provenance verifier exactly once"
    )


# ------------------------------------------------------------
# Behavioral verifier contract.
# ------------------------------------------------------------

if VERIFY.is_file():
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)

        build = temp / "build"
        stage = temp / "stage"
        artifacts = temp / "artifacts"

        build_payloads = {
            "AccountManager":
                b"real-account-dll\n",

            "ControlCenter":
                b"real-control-center-dll\n",

            "ControlWeb":
                b"real-control-web-dll\n",

            "PlaytimeGoals":
                b"real-playtime-goals-dll\n",
        }

        for plugin, payload in build_payloads.items():
            target = (
                build
                / plugin
                / "bin"
                / "Release"
                / "net10.0"
                / f"{plugin}.dll"
            )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_bytes(
                payload
            )

        web_assets = {
            "index.html":
                b"<html>verified</html>\n",

            "i18n.js":
                b"window.i18n={};\n",

            "core.js":
                b"window.Core={};\n",

            "qrcode.min.js":
                b"qr\n",

            "qrcode.LICENSE.txt":
                b"license\n",

            "app.js":
                b"console.log('verified');\n",

            "app.css":
                b"body{}\n",
        }

        web_build = (
            build
            / "ControlWeb"
            / "bin"
            / "Release"
            / "net10.0"
            / "www"
        )

        web_build.mkdir(
            parents=True,
            exist_ok=True,
        )

        for name, payload in web_assets.items():
            (
                web_build
                / name
            ).write_bytes(
                payload
            )

        for plugin in (
            "AccountManager",
            "ControlCenter",
            "PlaytimeGoals",
        ):
            source = (
                build
                / plugin
                / "bin"
                / "Release"
                / "net10.0"
                / f"{plugin}.dll"
            )

            target = (
                stage
                / plugin
                / f"{plugin}.dll"
            )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copyfile(
                source,
                target,
            )

        control_stage = (
            stage
            / "ControlWeb"
        )

        control_stage.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copyfile(
            (
                build
                / "ControlWeb"
                / "bin"
                / "Release"
                / "net10.0"
                / "ControlWeb.dll"
            ),
            (
                control_stage
                / "ControlWeb.dll"
            ),
        )

        shutil.copytree(
            web_build,
            control_stage / "www",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(ZIPPER),
                "--stage",
                str(stage),
                "--out",
                str(artifacts),
                "--suite-version",
                suite_version,
                "--playtimegoals-version",
                ptg_version,
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            errors.append(
                "failed to create provenance test ZIPs:\n"
                + result.stdout
                + result.stderr
            )

        metadata_name = (
            "CONTROL-SUITE-METADATA.json"
        )

        metadata = {
            "schemaVersion": 1,

            "release": {
                "controlSuiteVersion":
                    suite_version,

                "controlModuleVersion":
                    pins[
                        "CONTROL_MODULE_VERSION"
                    ],

                "playtimeGoalsVersion":
                    ptg_version,
            },

            "targets": {
                "asfVersion":
                    pins[
                        "ASF_VERSION"
                    ],

                "asfCommit":
                    pins[
                        "ASF_COMMIT"
                    ],

                "asfUiCommit":
                    pins[
                        "ASF_UI_COMMIT"
                    ],

                "playtimeGoalsCommit":
                    pins[
                        "PLAYTIMEGOALS_COMMIT"
                    ],

                "dotnetSdkVersion":
                    pins[
                        "DOTNET_SDK_VERSION"
                    ],
            },

            "install": {
                "extractInto":
                    "<ASF>/plugins/",

                "webPath":
                    "/Control/",
            },

            "artifacts": [
                (
                    "ASF-Control-Suite-v"
                    f"{suite_version}.zip"
                ),
                (
                    "AccountManager-v"
                    f"{suite_version}.zip"
                ),
                (
                    "ControlCenter-v"
                    f"{suite_version}.zip"
                ),
                (
                    "ControlWeb-v"
                    f"{suite_version}.zip"
                ),
            ],
        }

        artifacts.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            artifacts
            / metadata_name
        ).write_text(
            json.dumps(
                metadata,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        checksum_names = (
            metadata["artifacts"]
            + [metadata_name]
        )

        (
            artifacts
            / "SHA256SUMS"
        ).write_text(
            "".join(
                (
                    f"{sha256(artifacts / name)}  "
                    f"{name}\n"
                )
                for name in checksum_names
            ),
            encoding="utf-8",
        )

        command = [
            sys.executable,
            str(VERIFY),
            "--build-root",
            str(build),
            "--artifacts",
            str(artifacts),
            "--pins",
            str(PINS),
        ]

        clean = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if clean.returncode != 0:
            errors.append(
                "valid release provenance rejected:\n"
                + clean.stdout
                + clean.stderr
            )

        # ----------------------------------------------------
        # Tamper #1:
        # individual archive gets a different DLL while its
        # checksum is updated. SHA256SUMS alone therefore passes,
        # but byte identity against the build/bundle must fail.
        # ----------------------------------------------------

        account_zip = (
            artifacts
            / (
                "AccountManager-v"
                f"{suite_version}.zip"
            )
        )

        with zipfile.ZipFile(
            account_zip,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                "AccountManager/AccountManager.dll",
                b"tampered-account-dll\n",
            )

        (
            artifacts
            / "SHA256SUMS"
        ).write_text(
            "".join(
                (
                    f"{sha256(artifacts / name)}  "
                    f"{name}\n"
                )
                for name in checksum_names
            ),
            encoding="utf-8",
        )

        tampered = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if tampered.returncode == 0:
            errors.append(
                "tampered individual ZIP passed provenance verification after checksums were recomputed"
            )

        # Restore canonical individual archive.
        shutil.rmtree(
            artifacts,
        )

        artifacts.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(ZIPPER),
                "--stage",
                str(stage),
                "--out",
                str(artifacts),
                "--suite-version",
                suite_version,
                "--playtimegoals-version",
                ptg_version,
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            errors.append(
                "failed to recreate canonical provenance fixture"
            )

        (
            artifacts
            / metadata_name
        ).write_text(
            json.dumps(
                metadata,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            artifacts
            / "SHA256SUMS"
        ).write_text(
            "".join(
                (
                    f"{sha256(artifacts / name)}  "
                    f"{name}\n"
                )
                for name in checksum_names
            ),
            encoding="utf-8",
        )

        # ----------------------------------------------------
        # Tamper #2:
        # metadata commit changed and checksums recomputed.
        # Must still fail because pins are authoritative.
        # ----------------------------------------------------

        bad_metadata = dict(metadata)

        bad_metadata["targets"] = dict(
            metadata["targets"]
        )

        bad_metadata[
            "targets"
        ][
            "asfCommit"
        ] = (
            "0" * 40
        )

        (
            artifacts
            / metadata_name
        ).write_text(
            json.dumps(
                bad_metadata,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            artifacts
            / "SHA256SUMS"
        ).write_text(
            "".join(
                (
                    f"{sha256(artifacts / name)}  "
                    f"{name}\n"
                )
                for name in checksum_names
            ),
            encoding="utf-8",
        )

        wrong_metadata = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if wrong_metadata.returncode == 0:
            errors.append(
                "metadata contradicting release pins unexpectedly passed provenance verification"
            )


if errors:
    print(
        "RELEASE PROVENANCE CONTRACT: FAIL"
    )

    for error in errors:
        print(
            " -",
            error,
        )

    raise SystemExit(1)

print(
    "RELEASE PROVENANCE CONTRACT: PASS"
)
