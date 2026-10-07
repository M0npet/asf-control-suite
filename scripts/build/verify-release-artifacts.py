#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path


REQUIRED_PINS = (
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

CONTROLWEB_ASSETS = (
    "app.css",
    "app.js",
    "core.js",
    "i18n.js",
    "index.html",
    "qrcode.LICENSE.txt",
    "qrcode.min.js",
)


def fail(
    message: str,
) -> None:
    print(
        f"RELEASE PROVENANCE: FAIL: {message}",
        file=sys.stderr,
    )

    raise SystemExit(1)


def sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def parse_pins(
    path: Path,
) -> dict[str, str]:
    if not path.is_file():
        fail(
            f"pins file missing: {path}"
        )

    result: dict[str, str] = {}

    for number, raw in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        if "=" not in line:
            fail(
                f"malformed pin line {number}"
            )

        key, value = line.split(
            "=",
            1,
        )

        if (
            not key
            or not value
        ):
            fail(
                f"empty pin key/value on line {number}"
            )

        if key in result:
            fail(
                f"duplicate pin: {key}"
            )

        result[key] = value

    missing = [
        key
        for key in REQUIRED_PINS
        if key not in result
    ]

    if missing:
        fail(
            "required pins missing: "
            + ", ".join(missing)
        )

    return result


def public_ptg_version(
    version: str,
) -> str:
    parts = version.split(".")

    if (
        len(parts) == 4
        and parts[-1] == "0"
    ):
        return ".".join(
            parts[:-1]
        )

    return version


def expected_members() -> dict[str, set[str]]:
    control_web = {
        "ControlWeb/ControlWeb.dll",
    }

    control_web.update(
        {
            f"ControlWeb/www/{asset}"
            for asset in CONTROLWEB_ASSETS
        }
    )

    return {
        "AccountManager": {
            "AccountManager/AccountManager.dll",
        },

        "ControlCenter": {
            "ControlCenter/ControlCenter.dll",
        },

        "ControlWeb":
            control_web,

        "PlaytimeGoals": {
            "PlaytimeGoals/PlaytimeGoals.dll",
        },
        "Runtime": {
            "ArchiSteamFarm",
        },
    }


def expected_build_sources(
    build_root: Path,
) -> dict[str, Path]:
    result = {
        "AccountManager/AccountManager.dll":
            build_root
            / "AccountManager"
            / "bin"
            / "Release"
            / "net10.0"
            / "AccountManager.dll",

        "ControlCenter/ControlCenter.dll":
            build_root
            / "ControlCenter"
            / "bin"
            / "Release"
            / "net10.0"
            / "ControlCenter.dll",

        "ControlWeb/ControlWeb.dll":
            build_root
            / "ControlWeb"
            / "bin"
            / "Release"
            / "net10.0"
            / "ControlWeb.dll",

        "PlaytimeGoals/PlaytimeGoals.dll":
            build_root
            / "PlaytimeGoals"
            / "bin"
            / "Release"
            / "net10.0"
            / "PlaytimeGoals.dll",

        "ArchiSteamFarm":
            build_root
            / "out"
            / "control-suite-linux-arm64"
            / "ArchiSteamFarm",
    }

    for asset in CONTROLWEB_ASSETS:
        result[
            f"ControlWeb/www/{asset}"
        ] = (
            build_root
            / "ControlWeb"
            / "bin"
            / "Release"
            / "net10.0"
            / "www"
            / asset
        )

    return result


def read_zip_payloads(
    archive_path: Path,
    expected: set[str],
) -> dict[str, bytes]:
    if not archive_path.is_file():
        fail(
            f"archive missing: {archive_path.name}"
        )

    try:
        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:
            bad_member = archive.testzip()

            if bad_member is not None:
                fail(
                    f"{archive_path.name}: CRC failure in {bad_member}"
                )

            infos = archive.infolist()

            if any(
                info.is_dir()
                for info in infos
            ):
                fail(
                    f"{archive_path.name}: directory entries are forbidden"
                )

            names = [
                info.filename
                for info in infos
            ]

            if len(names) != len(set(names)):
                fail(
                    f"{archive_path.name}: duplicate ZIP member"
                )

            actual = set(names)

            if actual != expected:
                fail(
                    f"{archive_path.name}: member layout mismatch; "
                    f"expected={sorted(expected)!r}; "
                    f"actual={sorted(actual)!r}"
                )

            for info in infos:
                name = info.filename

                if (
                    name.startswith("/")
                    or "\\" in name
                    or ".." in Path(name).parts
                ):
                    fail(
                        f"{archive_path.name}: unsafe member path {name!r}"
                    )

                mode = (
                    info.external_attr >> 16
                )

                if mode:
                    kind = stat.S_IFMT(
                        mode
                    )

                    if kind not in (
                        0,
                        stat.S_IFREG,
                    ):
                        fail(
                            f"{archive_path.name}: non-regular ZIP member {name!r}"
                        )

                if (
                    name == "ArchiSteamFarm"
                    and not (mode & 0o111)
                ):
                    fail(
                        f"{archive_path.name}: ASF runtime is not executable"
                    )

            return {
                name: archive.read(name)
                for name in names
            }

    except zipfile.BadZipFile as exc:
        fail(
            f"{archive_path.name}: invalid ZIP: {exc}"
        )

    raise AssertionError(
        "unreachable"
    )


def verify_metadata(
    artifacts: Path,
    pins: dict[str, str],
    artifact_names: list[str],
) -> None:
    path = (
        artifacts
        / "CONTROL-SUITE-METADATA.json"
    )

    if not path.is_file():
        fail(
            "CONTROL-SUITE-METADATA.json missing"
        )

    try:
        actual = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        fail(
            f"invalid release metadata: {exc}"
        )

    expected = {
        "schemaVersion": 1,

        "release": {
            "controlModuleVersion":
                pins[
                    "CONTROL_MODULE_VERSION"
                ],

            "controlSuiteVersion":
                pins[
                    "CONTROL_SUITE_VERSION"
                ],

            "playtimeGoalsVersion":
                pins[
                    "PLAYTIMEGOALS_VERSION"
                ],
        },

        "targets": {
            "asfCommit":
                pins[
                    "ASF_COMMIT"
                ],

            "asfPatchSha256":
                pins[
                    "ASF_PATCH_SHA256"
                ],

            "asfUiCommit":
                pins[
                    "ASF_UI_COMMIT"
                ],

            "asfVersion":
                pins[
                    "ASF_VERSION"
                ],

            "dotnetSdkVersion":
                pins[
                    "DOTNET_SDK_VERSION"
                ],

            "playtimeGoalsCommit":
                pins[
                    "PLAYTIMEGOALS_COMMIT"
                ],
        },

        "install": {
            "extractInto":
                "<ASF>/",

            "webPath":
                "/",

            "canonicalControlPath":
                "/Control/",
        },

        "artifacts":
            artifact_names,
    }

    if actual != expected:
        fail(
            "CONTROL-SUITE-METADATA.json does not exactly match canonical release pins/layout"
        )


def verify_checksums(
    artifacts: Path,
    expected_names: list[str],
) -> None:
    path = (
        artifacts
        / "SHA256SUMS"
    )

    if not path.is_file():
        fail(
            "SHA256SUMS missing"
        )

    rows: dict[str, str] = {}

    pattern = re.compile(
        r"^([0-9a-f]{64})  ([^/\\]+)$"
    )

    for number, raw in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        match = pattern.fullmatch(
            raw
        )

        if match is None:
            fail(
                f"malformed SHA256SUMS line {number}"
            )

        digest, name = (
            match.group(1),
            match.group(2),
        )

        if name in rows:
            fail(
                f"duplicate SHA256SUMS entry: {name}"
            )

        rows[name] = digest

    if set(rows) != set(
        expected_names
    ):
        fail(
            "SHA256SUMS asset set mismatch; "
            f"expected={sorted(expected_names)!r}; "
            f"actual={sorted(rows)!r}"
        )

    for name in expected_names:
        artifact = (
            artifacts
            / name
        )

        if not artifact.is_file():
            fail(
                f"checksummed artifact missing: {name}"
            )

        actual = sha256(
            artifact
        )

        expected = rows[
            name
        ]

        if actual != expected:
            fail(
                f"SHA256 mismatch for {name}: "
                f"expected {expected}, got {actual}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify ASF Control Suite release provenance, "
            "canonical pins and byte identity."
        ),
    )

    parser.add_argument(
        "--build-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--artifacts",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--pins",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    build_root = (
        args.build_root.resolve()
    )

    artifacts = (
        args.artifacts.resolve()
    )

    pins = parse_pins(
        args.pins.resolve()
    )

    if not build_root.is_dir():
        fail(
            f"build root missing: {build_root}"
        )

    if not artifacts.is_dir():
        fail(
            f"artifacts directory missing: {artifacts}"
        )

    suite_version = pins[
        "CONTROL_SUITE_VERSION"
    ]

    ptg_public = public_ptg_version(
        pins[
            "PLAYTIMEGOALS_VERSION"
        ]
    )

    # Public Control Suite release ownership is intentionally
    # narrower than the canonical build output. The standalone
    # PlaytimeGoals ZIP is built and verified below, but is published
    # by the separate PlaytimeGoals release.
    public_artifact_names = [
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
    ]

    checksum_names = (
        public_artifact_names
        + [
            "CONTROL-SUITE-METADATA.json",
        ]
    )

    verify_metadata(
        artifacts,
        pins,
        public_artifact_names,
    )

    verify_checksums(
        artifacts,
        checksum_names,
    )

    groups = expected_members()

    plugin_members = set().union(
        groups["AccountManager"],
        groups["ControlCenter"],
        groups["ControlWeb"],
        groups["PlaytimeGoals"],
    )

    bundle_expected = {
        "ArchiSteamFarm",
        *(f"plugins/{relative}" for relative in plugin_members),
    }

    bundle_name = (
        "ASF-Control-Suite-v"
        f"{suite_version}.zip"
    )

    bundle = read_zip_payloads(
        artifacts / bundle_name,
        bundle_expected,
    )

    individual_names = {
        "AccountManager":
            (
                "AccountManager-v"
                f"{suite_version}.zip"
            ),

        "ControlCenter":
            (
                "ControlCenter-v"
                f"{suite_version}.zip"
            ),

        "ControlWeb":
            (
                "ControlWeb-v"
                f"{suite_version}.zip"
            ),

        "PlaytimeGoals":
            (
                "PlaytimeGoals-v"
                f"{ptg_public}.zip"
            ),
    }

    individual_payloads: dict[
        str,
        bytes,
    ] = {}

    for plugin, archive_name in (
        individual_names.items()
    ):
        payloads = read_zip_payloads(
            artifacts / archive_name,
            groups[plugin],
        )

        individual_payloads.update(
            payloads
        )

    sources = expected_build_sources(
        build_root
    )

    source_expected = (
        plugin_members
        | {"ArchiSteamFarm"}
    )

    if set(sources) != source_expected:
        fail(
            "internal build-source/member map mismatch"
        )

    for relative in sorted(source_expected):
        source = sources[relative]

        if not source.is_file():
            fail(
                f"build output missing: {source}"
            )

        build_bytes = source.read_bytes()

        if not build_bytes:
            fail(
                f"build output empty: {source}"
            )

        bundle_name_for_source = (
            relative
            if relative == "ArchiSteamFarm"
            else f"plugins/{relative}"
        )

        bundle_bytes = bundle[
            bundle_name_for_source
        ]

        if bundle_bytes != build_bytes:
            fail(
                "build -> bundle byte mismatch: "
                + relative
            )

        if relative == "ArchiSteamFarm":
            continue

        individual_bytes = (
            individual_payloads[
                relative
            ]
        )

        if individual_bytes != build_bytes:
            fail(
                "build -> individual byte mismatch: "
                + relative
            )

        if individual_bytes != bundle_bytes:
            fail(
                "bundle -> individual byte mismatch: "
                + relative
            )

    print(
        "RELEASE PROVENANCE: PASS"
    )

    print(
        "PINS -> METADATA -> CHECKSUMS -> "
        "BUILD -> BUNDLE -> INDIVIDUAL: PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
