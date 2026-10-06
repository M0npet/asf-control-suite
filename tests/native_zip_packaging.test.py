from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]

PACKAGE = (
    ROOT
    / "scripts"
    / "build"
    / "package-release.sh"
)

ZIPPER = (
    ROOT
    / "scripts"
    / "build"
    / "create-native-zips.py"
)

errors = []


# ------------------------------------------------------------
# package-release.sh must stage once and emit native ASF assets.
# ------------------------------------------------------------

if not PACKAGE.is_file():
    errors.append(
        "package-release.sh missing"
    )
else:
    text = PACKAGE.read_text(
        encoding="utf-8"
    )

    forbidden = (
        "asf-control-suite-v1.0-dist",
        ".tar.gz",
        '"$OUT/installer"',
        '"$OUT/plugins"',
    )

    for token in forbidden:
        if token in text:
            errors.append(
                f"transitional packaging remains: {token}"
            )

    required = (
        "STAGE_ROOT",
        "create-native-zips.py",
        "ASF-Control-Suite-v$CONTROL_SUITE_VERSION.zip",
        "AccountManager-v$CONTROL_SUITE_VERSION.zip",
        "ControlCenter-v$CONTROL_SUITE_VERSION.zip",
        "ControlWeb-v$CONTROL_SUITE_VERSION.zip",
        "PlaytimeGoals-v${PLAYTIMEGOALS_VERSION%.0}.zip",
        "CONTROL-SUITE-METADATA.json",
        "SHA256SUMS",
    )

    for token in required:
        if token not in text:
            errors.append(
                f"package-release.sh missing native packaging construct: {token}"
            )

    if text.count(
        "create-native-zips.py"
    ) != 1:
        errors.append(
            "package-release.sh must invoke the canonical ZIP creator exactly once"
        )


# ------------------------------------------------------------
# Pure deterministic ZIP creator contract.
# ------------------------------------------------------------

if not ZIPPER.is_file():
    errors.append(
        "scripts/build/create-native-zips.py missing"
    )

else:
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        stage = temp / "stage"
        out1 = temp / "out1"
        out2 = temp / "out2"

        runtime = temp / "ArchiSteamFarm"
        runtime.write_bytes(b"patched-asf-runtime\n")
        runtime.chmod(0o755)

        fixture = {
            "AccountManager/AccountManager.dll":
                b"account-manager-dll\n",

            "ControlCenter/ControlCenter.dll":
                b"control-center-dll\n",

            "ControlWeb/ControlWeb.dll":
                b"control-web-dll\n",

            "ControlWeb/www/index.html":
                b"<html>control</html>\n",

            "ControlWeb/www/app.js":
                b"console.log('control');\n",

            "PlaytimeGoals/PlaytimeGoals.dll":
                b"playtime-goals-dll\n",
        }

        for relative, payload in fixture.items():
            target = stage / relative
            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            target.write_bytes(payload)

        def run_packager(out: Path):
            result = subprocess.run(
                [
                    sys.executable,
                    str(ZIPPER),
                    "--stage",
                    str(stage),
                    "--runtime",
                    str(runtime),
                    "--out",
                    str(out),
                    "--suite-version",
                    "1.0.0",
                    "--playtimegoals-version",
                    "0.5.1.0",
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                errors.append(
                    "native ZIP creator failed:\n"
                    + result.stdout
                    + result.stderr
                )

            return result

        first = run_packager(out1)
        second = run_packager(out2)

        if (
            first.returncode == 0
            and second.returncode == 0
        ):
            expected_names = {
                "ASF-Control-Suite-v1.0.0.zip",
                "AccountManager-v1.0.0.zip",
                "ControlCenter-v1.0.0.zip",
                "ControlWeb-v1.0.0.zip",
                "PlaytimeGoals-v0.5.1.zip",
            }

            actual1 = {
                path.name
                for path in out1.glob("*.zip")
            }

            actual2 = {
                path.name
                for path in out2.glob("*.zip")
            }

            if actual1 != expected_names:
                errors.append(
                    "unexpected first ZIP set: "
                    + repr(sorted(actual1))
                )

            if actual2 != expected_names:
                errors.append(
                    "unexpected second ZIP set: "
                    + repr(sorted(actual2))
                )

            expected_members = {
                "AccountManager-v1.0.0.zip": {
                    "AccountManager/AccountManager.dll",
                },

                "ControlCenter-v1.0.0.zip": {
                    "ControlCenter/ControlCenter.dll",
                },

                "ControlWeb-v1.0.0.zip": {
                    "ControlWeb/ControlWeb.dll",
                    "ControlWeb/www/index.html",
                    "ControlWeb/www/app.js",
                },

                "PlaytimeGoals-v0.5.1.zip": {
                    "PlaytimeGoals/PlaytimeGoals.dll",
                },

                "ASF-Control-Suite-v1.0.0.zip": {
                    "ArchiSteamFarm",
                    *(f"plugins/{name}" for name in fixture),
                },
            }

            bundle_payloads = {}

            for archive_name, expected in expected_members.items():
                archive = out1 / archive_name

                if not archive.is_file():
                    continue

                with zipfile.ZipFile(
                    archive,
                    "r",
                ) as handle:
                    names = {
                        info.filename
                        for info in handle.infolist()
                        if not info.is_dir()
                    }

                    if names != expected:
                        errors.append(
                            f"{archive_name}: unexpected members "
                            f"{sorted(names)!r}"
                        )

                    if archive_name == "ASF-Control-Suite-v1.0.0.zip":
                        runtime_info = archive.getinfo("ArchiSteamFarm")
                        runtime_mode = runtime_info.external_attr >> 16
                        if not (runtime_mode & 0o111):
                            errors.append(
                                "ASF runtime executable mode missing"
                            )

                    for name in names:
                        if name.startswith("installer/"):
                            errors.append(
                                f"{archive_name}: forbidden prefix {name}"
                            )

                        if (
                            archive_name != "ASF-Control-Suite-v1.0.0.zip"
                            and name.startswith("plugins/")
                        ):
                            errors.append(
                                f"{archive_name}: forbidden prefix {name}"
                            )

                        if name in (
                            "BUILD-METADATA.txt",
                            "INSTALL-LAYOUT.txt",
                            "CONTROL-SUITE-METADATA.json",
                            "SHA256SUMS",
                        ):
                            errors.append(
                                f"{archive_name}: release metadata embedded in plugin ZIP"
                            )

                    if archive_name == "ASF-Control-Suite-v1.0.0.zip":
                        bundle_payloads = {
                            name: handle.read(name)
                            for name in names
                        }

            # Every individual file must be byte-identical to
            # the same member in the bundle.
            for archive_name in (
                "AccountManager-v1.0.0.zip",
                "ControlCenter-v1.0.0.zip",
                "ControlWeb-v1.0.0.zip",
                "PlaytimeGoals-v0.5.1.zip",
            ):
                archive = out1 / archive_name

                if not archive.is_file():
                    continue

                with zipfile.ZipFile(
                    archive,
                    "r",
                ) as handle:
                    for info in handle.infolist():
                        if info.is_dir():
                            continue

                        payload = handle.read(
                            info.filename
                        )

                        if (
                            bundle_payloads.get(
                                f"plugins/{info.filename}"
                            )
                            != payload
                        ):
                            errors.append(
                                f"{archive_name}: bundle byte mismatch for {info.filename}"
                            )

            # Same canonical stage must produce deterministic ZIP bytes.
            for name in expected_names:
                one = out1 / name
                two = out2 / name

                if not (
                    one.is_file()
                    and two.is_file()
                ):
                    continue

                digest1 = hashlib.sha256(
                    one.read_bytes()
                ).hexdigest()

                digest2 = hashlib.sha256(
                    two.read_bytes()
                ).hexdigest()

                if digest1 != digest2:
                    errors.append(
                        f"{name}: ZIP output is not deterministic"
                    )


if errors:
    print(
        "NATIVE ZIP PACKAGING CONTRACT: FAIL"
    )

    for error in errors:
        print(" -", error)

    raise SystemExit(1)

print(
    "NATIVE ZIP PACKAGING CONTRACT: PASS"
)
