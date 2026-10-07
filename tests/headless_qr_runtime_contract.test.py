from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

patch = ROOT / "patches/asf/0001-headless-qr-ipc.patch"
apply_script = ROOT / "scripts/build/apply-asf-patches.sh"
prepare = ROOT / "scripts/build/prepare-release-worktree.sh"
build = ROOT / "scripts/build/build-release.sh"
package = ROOT / "scripts/build/package-release.sh"
zipper = ROOT / "scripts/build/create-native-zips.py"
transaction = ROOT / "installer/phone-transaction.sh"
rollback = ROOT / "installer/phone-rollback-core.sh"
verify = ROOT / "scripts/phone/phone-verify-via-adb.sh"

errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

require(patch.is_file(), "ASF headless QR patch is missing")
if patch.is_file():
    text = patch.read_text(encoding="utf-8")
    require("WantsQrCodeLogin" in text, "patch does not modify WantsQrCodeLogin")
    require("RequiredInput = ASF.EUserInputType.QrCodeLogin" in text, "patch does not expose QR input state")
    require("QrCodeLoginInput" in text, "patch does not consume IPC QR confirmation")
    require("Task.Delay(100)" in text, "patch does not wait asynchronously for IPC confirmation")
    require(
        "string qrDecision = QrCodeLoginInput;" in text,
        "patch does not use a non-conflicting QR decision variable",
    )
    require(
        "string input = QrCodeLoginInput;" not in text,
        "patch shadows upstream WantsQrCodeLogin input variable",
    )
    require("ControlSuiteQrSteamLogin" in text, "patch does not persist QR-derived login identity in bot database")
    require("BotDatabase.QrSteamLogin = pollResult.AccountName" in text, "patch does not save the authenticated QR account name")
    require("BotDatabase.QrSteamLogin" in text and "SetUserInput(ASF.EUserInputType.Login, BotDatabase.QrSteamLogin)" in text, "patch does not restore the QR login identity after bot reload")
    require("BotConfig.Saving = true" not in text, "patch must not rewrite BotConfig from the QR login callback")
    require("ArchiSteamFarm.Steam.Storage.BotConfig.Write" not in text, "patch must not trigger a BotConfig write/reload from QR login")

require(apply_script.is_file(), "ASF patch application script is missing")
if apply_script.is_file():
    text = apply_script.read_text(encoding="utf-8")
    require("git apply --check" in text, "ASF patch is not preflight-checked")
    require("ASF_PATCH_SHA256" in text, "ASF patch digest is not verified")
    require(
        'git -C "$ROOT" rev-parse --is-inside-work-tree' in text,
        "ASF patch application does not accept linked git worktrees",
    )
    require(
        '[[ -d "$ROOT/.git" ]]' not in text,
        "ASF patch application incorrectly requires .git to be a directory",
    )

prepare_text = prepare.read_text(encoding="utf-8")
require("apply-asf-patches.sh" in prepare_text, "release worktree does not apply ASF compatibility patch")

build_text = build.read_text(encoding="utf-8")
require("dotnet publish" in build_text, "build does not publish patched ASF runtime")
require("-p:ASFVariant=linux-arm64" in build_text, "ASF runtime is not built as linux-arm64")
require("-p:PublishSingleFile=true" in build_text, "ASF runtime is not single-file")
require("-p:PublishTrimmed=true" in build_text, "ASF runtime is not trimmed")
require("-r linux-arm64" in build_text, "ASF runtime RID is not linux-arm64")
require("--self-contained" in build_text, "ASF runtime is not self-contained")
require('ASF_RUNTIME="$ASF_RUNTIME_DIR/ArchiSteamFarm"' in build_text, "build does not require patched ASF executable")

package_text = package.read_text(encoding="utf-8")
require("--runtime" in package_text, "packager does not receive patched ASF runtime")
require('ASF_RUNTIME="out/control-suite-linux-arm64/ArchiSteamFarm"' in package_text, "package stage does not include patched ASF executable")

zipper_text = zipper.read_text(encoding="utf-8")
require("--runtime" in zipper_text, "ZIP creator has no runtime input")
require('"ArchiSteamFarm"' in zipper_text, "suite bundle does not include ArchiSteamFarm executable")
require("EXECUTABLE_FILE_MODE" in zipper_text, "suite bundle does not preserve ASF executable mode")
require('f"plugins/{relative}"' in zipper_text, "suite bundle does not install plugins under plugins/")

for path, label in (
    (transaction, "phone transaction"),
    (rollback, "phone rollback"),
    (verify, "phone verify"),
):
    text = path.read_text(encoding="utf-8")
    require("ArchiSteamFarm" in text, f"{label} does not manage patched ASF runtime")

if errors:
    print("HEADLESS QR RUNTIME CONTRACT: FAIL")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print("HEADLESS QR RUNTIME CONTRACT: PASS")
