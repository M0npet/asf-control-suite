from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/asf/0001-headless-qr-ipc.patch"

text = PATCH.read_text(encoding="utf-8").splitlines()

hunk_re = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)

errors = []
hunks = 0
i = 0

while i < len(text):
    line = text[i]
    match = hunk_re.match(line)

    if match is None:
        i += 1
        continue

    hunks += 1
    expected_old = int(match.group(2) or "1")
    expected_new = int(match.group(4) or "1")

    old_count = 0
    new_count = 0
    i += 1

    while i < len(text):
        body = text[i]

        if body.startswith("@@ ") or body.startswith("diff --git "):
            break

        if body.startswith("\\ No newline at end of file"):
            i += 1
            continue

        if body.startswith("--- ") or body.startswith("+++ "):
            break

        if not body:
            if i == len(text) - 1:
                i += 1
                continue
            errors.append(f"line {i + 1}: empty patch body line has no diff prefix")
            i += 1
            continue

        prefix = body[0]

        if prefix == " ":
            old_count += 1
            new_count += 1
        elif prefix == "-":
            old_count += 1
        elif prefix == "+":
            new_count += 1
        else:
            errors.append(
                f"line {i + 1}: invalid hunk body prefix {prefix!r}"
            )

        i += 1

    if old_count != expected_old or new_count != expected_new:
        errors.append(
            f"{line}: body counts old={old_count}, new={new_count}; "
            f"header expects old={expected_old}, new={expected_new}"
        )

if hunks == 0:
    errors.append("patch contains no hunks")

if errors:
    print("ASF PATCH STRUCTURE: FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print(f"ASF PATCH STRUCTURE: PASS ({hunks} hunks)")
