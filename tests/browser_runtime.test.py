from pathlib import Path
from tempfile import TemporaryDirectory

from browser_runtime import resolve_chromium_executable


def check(condition, message):
    if not condition:
        raise AssertionError(message)


override = "/custom/chromium"
check(
    resolve_chromium_executable(
        environ={"CONTROL_CHROMIUM": override},
        candidates=("/ignored/system/chromium",),
    ) == override,
    "CONTROL_CHROMIUM override must win",
)

with TemporaryDirectory() as tmp:
    first = Path(tmp) / "missing"
    second = Path(tmp) / "chromium"
    second.write_text("", encoding="utf-8")

    check(
        resolve_chromium_executable(
            environ={},
            candidates=(str(first), str(second)),
        ) == str(second),
        "first existing system Chromium candidate must be selected",
    )

check(
    resolve_chromium_executable(environ={}, candidates=()) is None,
    "no system browser must fall back to Playwright-managed Chromium",
)

print("BROWSER RUNTIME CONTRACT: PASS")
