from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_CHROMIUM_CANDIDATES = (
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
)


def resolve_chromium_executable(
    environ: Mapping[str, str] | None = None,
    candidates: Sequence[str] = DEFAULT_CHROMIUM_CANDIDATES,
) -> str | None:
    env = os.environ if environ is None else environ
    override = env.get("CONTROL_CHROMIUM")

    if override:
        return override

    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate

    return None
