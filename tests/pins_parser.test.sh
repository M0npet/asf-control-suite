#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
. "$ROOT/scripts/build/pins.sh"

load_release_pins "$ROOT/release/pins.env" || {
    echo 'PINS PARSER TEST: canonical file rejected'
    exit 1
}

for key in \
    CONTROL_SUITE_VERSION \
    CONTROL_MODULE_VERSION \
    ASF_VERSION \
    ASF_COMMIT \
    ASF_UI_COMMIT \
    PLAYTIMEGOALS_VERSION \
    PLAYTIMEGOALS_COMMIT \
    DOTNET_SDK_VERSION
do
    if [[ -z "${!key:-}" ]]; then
        echo "PINS PARSER TEST: missing parsed value: $key"
        exit 1
    fi
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp "$ROOT/release/pins.env" "$TMP/duplicate.env"
printf '%s\n' 'ASF_VERSION=1.2.3.4' >> "$TMP/duplicate.env"

if (
    load_release_pins "$TMP/duplicate.env"
) >/dev/null 2>&1; then
    echo 'PINS PARSER TEST: duplicate key accepted'
    exit 1
fi

cp "$ROOT/release/pins.env" "$TMP/unknown.env"
printf '%s\n' 'TOTALLY_UNKNOWN_KEY=value' >> "$TMP/unknown.env"

if (
    load_release_pins "$TMP/unknown.env"
) >/dev/null 2>&1; then
    echo 'PINS PARSER TEST: unknown key accepted'
    exit 1
fi

MARKER="$TMP/should-not-exist"

python3 - "$ROOT/release/pins.env" "$TMP/injection.env" "$MARKER" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
target = Path(sys.argv[2])
marker = sys.argv[3]

lines = []

for line in source.splitlines():
    if line.startswith("ASF_VERSION="):
        lines.append(
            f"ASF_VERSION=$(touch${{IFS}}{marker})"
        )
    else:
        lines.append(line)

target.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)
PY

if (
    load_release_pins "$TMP/injection.env"
) >/dev/null 2>&1; then
    echo 'PINS PARSER TEST: command-like value accepted'
    exit 1
fi

if [[ -e "$MARKER" ]]; then
    echo 'PINS PARSER TEST: input was executed'
    exit 1
fi

echo 'PINS PARSER TEST: PASS'
