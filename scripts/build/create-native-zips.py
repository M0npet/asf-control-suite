#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PLUGIN_NAMES = (
    "AccountManager",
    "ControlCenter",
    "ControlWeb",
    "PlaytimeGoals",
)

FIXED_ZIP_TIME = (
    1980,
    1,
    1,
    0,
    0,
    0,
)

REGULAR_FILE_MODE = 0o100644


def fail(message: str) -> None:
    raise SystemExit(message)


def validate_version(
    value: str,
    label: str,
) -> str:
    if not re.fullmatch(
        r"[0-9]+(?:\.[0-9]+){2,3}",
        value,
    ):
        fail(
            f"invalid {label}: {value!r}"
        )

    return value


def public_ptg_version(
    version: str,
) -> str:
    parts = version.split(".")

    if (
        len(parts) == 4
        and parts[-1] == "0"
    ):
        return ".".join(parts[:-1])

    return version


def collect_stage_members(
    stage: Path,
) -> dict[str, tuple[str, ...]]:
    if not stage.is_dir():
        fail(
            f"stage directory not found: {stage}"
        )

    unexpected = sorted(
        child.name
        for child in stage.iterdir()
        if child.name not in PLUGIN_NAMES
    )

    if unexpected:
        fail(
            "unexpected top-level stage entries: "
            + ", ".join(unexpected)
        )

    members: dict[
        str,
        tuple[str, ...],
    ] = {}

    for plugin in PLUGIN_NAMES:
        root = stage / plugin

        if not root.is_dir():
            fail(
                f"plugin stage missing: {plugin}"
            )

        if root.is_symlink():
            fail(
                f"symlinked plugin root forbidden: {plugin}"
            )

        paths: list[str] = []

        for path in sorted(
            root.rglob("*"),
            key=lambda item: item.as_posix(),
        ):
            if path.is_symlink():
                fail(
                    "symlink forbidden in native package stage: "
                    + path.relative_to(stage).as_posix()
                )

            if path.is_dir():
                continue

            if not path.is_file():
                fail(
                    "non-regular stage entry forbidden: "
                    + path.relative_to(stage).as_posix()
                )

            relative = (
                path.relative_to(stage)
                .as_posix()
            )

            if (
                relative.startswith("/")
                or ".." in Path(relative).parts
            ):
                fail(
                    f"unsafe stage path: {relative}"
                )

            paths.append(relative)

        if not paths:
            fail(
                f"plugin stage empty: {plugin}"
            )

        members[plugin] = tuple(paths)

    return members


def write_deterministic_zip(
    stage: Path,
    target: Path,
    members: tuple[str, ...],
) -> None:
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.unlink(
        missing_ok=True,
    )

    with ZipFile(
        target,
        mode="w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for relative in sorted(members):
            source = stage / relative

            payload = source.read_bytes()

            info = ZipInfo(
                filename=relative,
                date_time=FIXED_ZIP_TIME,
            )

            info.create_system = 3
            info.compress_type = ZIP_DEFLATED
            info.external_attr = (
                REGULAR_FILE_MODE << 16
            )

            archive.writestr(
                info,
                payload,
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create deterministic native ASF plugin ZIPs "
            "from one canonical stage."
        ),
    )

    parser.add_argument(
        "--stage",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--out",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--suite-version",
        required=True,
    )

    parser.add_argument(
        "--playtimegoals-version",
        required=True,
    )

    args = parser.parse_args()

    suite_version = validate_version(
        args.suite_version,
        "suite version",
    )

    ptg_version = validate_version(
        args.playtimegoals_version,
        "PlaytimeGoals version",
    )

    ptg_public = public_ptg_version(
        ptg_version
    )

    stage = args.stage.resolve()
    out = args.out.resolve()

    members = collect_stage_members(
        stage
    )

    bundle_members = tuple(
        relative
        for plugin in PLUGIN_NAMES
        for relative in members[plugin]
    )

    archives = {
        (
            f"ASF-Control-Suite-v"
            f"{suite_version}.zip"
        ): bundle_members,

        (
            f"AccountManager-v"
            f"{suite_version}.zip"
        ): members["AccountManager"],

        (
            f"ControlCenter-v"
            f"{suite_version}.zip"
        ): members["ControlCenter"],

        (
            f"ControlWeb-v"
            f"{suite_version}.zip"
        ): members["ControlWeb"],

        (
            f"PlaytimeGoals-v"
            f"{ptg_public}.zip"
        ): members["PlaytimeGoals"],
    }

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name in sorted(archives):
        target = out / name

        write_deterministic_zip(
            stage,
            target,
            archives[name],
        )

        print(
            f"{sha256(target)}  {name}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
