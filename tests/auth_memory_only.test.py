from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

APP = (
    ROOT
    / "src"
    / "ControlWeb"
    / "www"
    / "app.js"
)

INDEX = (
    ROOT
    / "src"
    / "ControlWeb"
    / "www"
    / "index.html"
)

I18N = (
    ROOT
    / "src"
    / "ControlWeb"
    / "www"
    / "i18n.js"
)

errors = []

for path in (APP, INDEX, I18N):
    if not path.is_file():
        errors.append(
            f"missing file: {path.relative_to(ROOT)}"
        )

if errors:
    print("RAM-ONLY AUTH CONTRACT: FAIL")

    for error in errors:
        print(" -", error)

    raise SystemExit(1)


app = APP.read_text(encoding="utf-8")
index = INDEX.read_text(encoding="utf-8")
i18n = I18N.read_text(encoding="utf-8")


# Password must begin empty on every document load.
if not re.search(
    r"\bpassword:\s*''\s*,",
    app,
):
    errors.append(
        "state.password is not initialized empty"
    )


# Password must continue to be used directly for native ASF Authentication.
if "headers.set('Authentication', state.password)" not in app:
    errors.append(
        "ASF Authentication header no longer uses in-memory state.password"
    )


# Successful authentication must move the supplied password into RAM.
if not re.search(
    r"async function authenticate\(password\).*?"
    r"state\.password\s*=\s*password\s*;",
    app,
    re.S,
):
    errors.append(
        "authenticate() does not populate in-memory state.password"
    )


# Lock/error paths must erase the in-memory credential.
if app.count("state.password = '';") < 2:
    errors.append(
        "insufficient in-memory password clearing paths"
    )


# The former persistent password key is forbidden entirely.
for forbidden in (
    "PASSWORD_KEY",
    "asf.control.ipcPassword",
):
    if forbidden in app:
        errors.append(
            f"app.js still contains persistent password marker: {forbidden}"
        )


# sessionStorage remains allowed only for non-secret UI preferences.
storage_calls = re.findall(
    r"sessionStorage\."
    r"(getItem|setItem|removeItem)"
    r"\(([^)]]*)\)",
    app,
)

if not storage_calls:
    errors.append(
        "non-secret sessionStorage preference persistence disappeared"
    )

for operation, arguments in storage_calls:
    if (
        "VIEW_KEY" not in arguments
        and "LOCK_KEY" not in arguments
    ):
        errors.append(
            "sessionStorage used for non-allowlisted data: "
            f"{operation}({arguments})"
        )


if "sessionStorage.getItem(VIEW_KEY)" not in app:
    errors.append(
        "view preference is no longer restored"
    )

if "sessionStorage.getItem(LOCK_KEY)" not in app:
    errors.append(
        "lock timeout preference is no longer restored"
    )

if "sessionStorage.setItem(VIEW_KEY" not in app:
    errors.append(
        "view preference is no longer persisted"
    )

if "sessionStorage.setItem(LOCK_KEY" not in app:
    errors.append(
        "lock timeout preference is no longer persisted"
    )


memory_copy = (
    "The IPC password is kept only in page memory "
    "and is lost on refresh, lock, or tab close."
)

if memory_copy not in app:
    errors.append(
        "Security UI does not describe RAM-only password handling"
    )

if memory_copy not in i18n:
    errors.append(
        "RAM-only Security UI string missing from i18n catalog"
    )

if (
    "It is kept only in page memory and is lost on "
    "refresh, lock, or tab close."
    not in index
):
    errors.append(
        "authentication screen does not describe refresh semantics"
    )


old_copy = (
    "The IPC password exists only in sessionStorage "
    "and is cleared when the session locks."
)

if old_copy in app or old_copy in i18n:
    errors.append(
        "obsolete sessionStorage password claim remains"
    )


if errors:
    print("RAM-ONLY AUTH CONTRACT: FAIL")

    for error in errors:
        print(" -", error)

    sys.exit(1)

print("RAM-ONLY AUTH CONTRACT: PASS")
