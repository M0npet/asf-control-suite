from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "scripts" / "build" / "package-release.sh"

errors: list[str] = []

text = PACKAGE.read_text(encoding="utf-8")


# ------------------------------------------------------------
# The canonical Control Suite build may create the standalone
# PlaytimeGoals ZIP so provenance can verify byte identity.
#
# However, that standalone ZIP belongs to the PlaytimeGoals
# public release, not to the Control Suite public release.
# ------------------------------------------------------------

metadata_call = re.search(
    r'python3\s+-\s+\\\n'
    r'.*?'
    r'<<[\'"]?PY[\'"]?',
    text,
    re.DOTALL,
)

if metadata_call is None:
    errors.append(
        "could not locate CONTROL-SUITE-METADATA generator invocation"
    )
else:
    block = metadata_call.group(0)

    if '$(basename "$PTG_ZIP")' in block:
        errors.append(
            "Control Suite metadata still receives the standalone "
            "PlaytimeGoals ZIP as a public artifact"
        )


checksum_block = re.search(
    r'sha256sum\s+\\\n'
    r'.*?'
    r'>\s*"SHA256SUMS"',
    text,
    re.DOTALL,
)

if checksum_block is None:
    errors.append(
        "could not locate Control Suite SHA256SUMS generation"
    )
else:
    block = checksum_block.group(0)

    if '$(basename "$PTG_ZIP")' in block:
        errors.append(
            "Control Suite SHA256SUMS still includes the standalone "
            "PlaytimeGoals ZIP"
        )


# The standalone PTG ZIP itself must still be built.
if 'PTG_ZIP=' not in text:
    errors.append(
        "canonical build no longer defines a standalone PlaytimeGoals ZIP"
    )

if '"$PTG_ZIP"' not in text:
    errors.append(
        "canonical build no longer retains the PlaytimeGoals ZIP"
    )


if errors:
    print("PUBLIC RELEASE ASSET OWNERSHIP CONTRACT: FAIL")

    for error in errors:
        print(" -", error)

    raise SystemExit(1)

print("PUBLIC RELEASE ASSET OWNERSHIP CONTRACT: PASS")
