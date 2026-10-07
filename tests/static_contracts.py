from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]

IGNORED_DIR_NAMES = {'.git', '.venv', '__pycache__', 'artifacts', 'bin', 'obj', 'node_modules'}

def project_files(extensions=None):
    for p in ROOT.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in IGNORED_DIR_NAMES for part in rel.parts[:-1]):
            continue
        if extensions is not None and p.suffix.lower() not in extensions:
            continue
        yield p


IGNORED_DIR_NAMES = {'.git', '.venv', '__pycache__', 'artifacts', 'bin', 'obj', 'node_modules'}

def project_files(extensions=None):
    for p in ROOT.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in IGNORED_DIR_NAMES for part in rel.parts[:-1]):
            continue
        if extensions is not None and p.suffix.lower() not in extensions:
            continue
        yield p


def text(path):
    return (ROOT/path).read_text(encoding='utf-8')

def require(path, needle, label=None):
    p=ROOT/path
    if not p.exists():
        errors.append(f'missing file: {path}'); return
    if needle not in p.read_text(encoding='utf-8'):
        errors.append(f'{label or needle!r} missing in {path}')

def require_re(path, pattern, label):
    if not re.search(pattern, text(path), re.M|re.S): errors.append(f'{label} missing in {path}')

def forbid(path, needle, label=None):
    if needle in text(path): errors.append(f'forbidden {label or needle!r} in {path}')

def forbid_tree(needle,label=None,extensions={'.cs','.js','.html'}):
    for p in project_files(extensions):
        try:t=p.read_text(encoding='utf-8')
        except UnicodeDecodeError:continue
        if needle in t:errors.append(f'forbidden {label or needle!r} in {p.relative_to(ROOT)}')

for project in ('AccountManager','ControlWeb'):
   require(f'src/{project}/{project}.csproj','<Version>1.0.0.0</Version>',f'{project} v1.0')
   require(f'src/{project}/{project}Plugin.cs','[Export(typeof(IPlugin))]',f'{project} export')
   require(f'src/{project}/{project}Plugin.cs','new Version(1, 0, 0, 0)',f'{project} fallback version')

require('src/ControlCenter/ControlCenter.csproj','<Version>1.0.0.0</Version>','ControlCenter v1.0')
require('src/ControlCenter/ControlCenterPlugin.cs','[Export(typeof(IPlugin))]','ControlCenter export')
require('src/ControlCenter/ControlCenterPlugin.cs','new Version(ControlModuleVersion)','ControlCenter canonical fallback version')

require('src/AccountManager/DefaultsStore.cs','MaxPayloadChars = 64 * 1024','defaults size limit')
require('src/AccountManager/DefaultsStore.cs','SensitiveMarkers','secret-like filtering')
require('src/AccountManager/DefaultsStore.cs','private static readonly SemaphoreSlim Sync = new(1, 1);','singleton semaphore must not trigger CA1001')
forbid('src/AccountManager/DefaultsStore.cs','ToLowerInvariant','CA1308 lowercasing regression')
require('src/AccountManager/DefaultsStore.cs','StringComparison.OrdinalIgnoreCase','case-insensitive secret marker matching')
require('src/AccountManager/AccountManagerController.cs','bot.AvatarHash','Steam avatar in account summary')
require('src/AccountManager/AccountManagerController.cs','QrChallengeUrl = bot.QrChallengeURL?.ToString()','native QR challenge in account summary')
require('src/ControlCenter/ControlCenterPlugin.cs','ControlSuiteVersion = BuildInfo.ControlSuiteVersion','generated suite version')
require('src/ControlCenter/ControlCenterPlugin.cs','ControlModuleVersion = BuildInfo.ControlModuleVersion','generated module version')
require('src/ControlCenter/ControlCenterPlugin.cs','TargetAsfVersion = BuildInfo.TargetAsfVersion','generated ASF version')
require('src/ControlCenter/ControlCenterPlugin.cs','TargetAsfCommit = BuildInfo.TargetAsfCommit','generated ASF commit')
require('src/ControlCenter/ControlCenterPlugin.cs','TargetAsfUiCommit = BuildInfo.TargetAsfUiCommit','generated ASF-ui commit')
require('src/ControlCenter/ControlCenterPlugin.cs','TargetPlaytimeGoalsVersion = BuildInfo.TargetPlaytimeGoalsVersion','generated PTG version')
require('src/ControlCenter/ControlCenterPlugin.cs','TargetPlaytimeGoalsCommit = BuildInfo.TargetPlaytimeGoalsCommit','generated PTG commit')
require('src/ControlCenter/ControlCenterController.cs','ControlSuiteVersion = ControlCenterPlugin.ControlSuiteVersion','suite version status metadata')
require('src/ControlCenter/ControlCenterController.cs','ControlModuleVersion = ControlCenterPlugin.ControlModuleVersion','module version status metadata')
require('src/ControlCenter/ControlCenterController.cs','TargetAsfUiCommit = ControlCenterPlugin.TargetAsfUiCommit','ASF-ui commit status metadata')
require('src/ControlCenter/ControlCenterController.cs','Module("PlaytimeGoals", ControlCenterPlugin.TargetPlaytimeGoalsVersion)','generated PTG module expectation')
require('src/ControlCenter/ControlCenterController.cs','Module("AccountManager", ControlCenterPlugin.ControlModuleVersion)','generated AccountManager module expectation')
require('src/ControlCenter/ControlCenterController.cs','Module("ControlCenter", ControlCenterPlugin.ControlModuleVersion)','generated ControlCenter module expectation')
require('src/ControlCenter/ControlCenterController.cs','Module("ControlWeb", ControlCenterPlugin.ControlModuleVersion)','generated ControlWeb module expectation')
forbid('src/ControlCenter/ControlCenterController.cs','Environment.','trim-unsafe Environment runtime metadata')
require('src/ControlCenter/ControlCenterController.cs','/Control/healthz','functional local health probe')
require('src/ControlCenter/ControlCenterController.cs','control-suite-health','functional health sentinel')
require('src/ControlCenter/ControlCenterController.cs','return Ok(new { Healthy = true, Probe = "control-suite-health" });','trim-safe health response via retained Ok(object) helper')
forbid('src/ControlCenter/ControlCenterController.cs','return Content(','trim-unsafe ControllerBase.Content helper')
forbid('src/ControlCenter/ControlCenterController.cs','return StatusCode(','avoid unverified trimmed MVC status helper in health path')
forbid('src/ControlCenter/ControlCenterController.cs','ApiExplorerSettings','trim-unsafe MVC metadata attribute')
require('src/ControlCenter/ControlCenterController.cs','StorageAvailable = false','trim-safe unavailable storage status')
require('src/ControlCenter/ControlCenterController.cs','DiskTotalBytes = (long?) null','trim-safe null disk total')
require('src/ControlCenter/ControlCenterController.cs','DiskFreeBytes = (long?) null','trim-safe null disk free')
forbid('src/ControlCenter/ControlCenterController.cs','System.IO','trim-unsafe direct System.IO dependency')
forbid('src/ControlCenter/ControlCenterController.cs','Path.','trim-unsafe Path dependency')
forbid('src/ControlCenter/ControlCenterController.cs','Directory.','trim-unsafe Directory dependency')
forbid('src/ControlCenter/ControlCenterController.cs','DriveInfo','trim-unsafe DriveInfo dependency')
forbid('src/ControlCenter/ControlCenterController.cs','RuntimeInformation','trim-unsafe RuntimeInformation dependency')
forbid('src/ControlCenter/ControlCenterController.cs','System.Runtime.InteropServices','trim-unsafe interop metadata dependency')

require('src/ControlWeb/www/index.html','Content-Security-Policy','CSP')
require('src/ControlWeb/www/index.html','https://avatars.akamai.steamstatic.com','Steam avatar CSP allowlist')
require('src/ControlWeb/www/index.html','no-referrer','referrer policy')
require('src/ControlWeb/www/index.html','aria-live="polite"','live region')
require('src/ControlWeb/www/index.html','<dialog id="modal"','native modal')
require('src/ControlWeb/www/index.html','Control Suite 1.0','release branding')
require_re('src/ControlWeb/www/app.js',r"cache\s*:\s*'no-store'",'API no-store')
require('src/ControlWeb/www/app.js','function toast(','toast system')
require('src/ControlWeb/www/app.js','function openModal(','modal system')
require('src/ControlWeb/www/app.js','function qrOnboardingMarkup(','inline QR onboarding panel')
require('src/ControlWeb/www/app.js','function updateQrOnboardingPanel(','targeted QR lifecycle updates')
require('src/ControlWeb/www/app.js','await maybeAcceptQrPrompt(latest);','QR retry prompt re-acceptance')
require('src/ControlWeb/www/app.js','QR login could not continue','terminal QR lifecycle surface')
require('src/ControlWeb/www/app.js','latestRequired > 0 && latestRequired !== QR_INPUT_TYPE','terminal non-QR input gate')
forbid('src/ControlWeb/www/app.js','qrAcceptedBots','one-shot QR acceptance state')
require('src/ControlWeb/www/app.js','managedStatusRows','managed status UI')
require('src/ControlWeb/www/app.js',"api('/Api/ControlCenter/Status')",'Advanced compatibility metadata API')
require('src/ControlWeb/www/app.js','control?.ControlSuiteVersion','dynamic suite version UI')
require('src/ControlWeb/www/app.js','control?.ControlModuleVersion','dynamic module version UI')
require('src/ControlWeb/www/app.js','control?.TargetAsfCommit','dynamic ASF commit UI')
require('src/ControlWeb/www/app.js','control?.TargetAsfUiCommit','dynamic ASF-ui commit UI')
require('src/ControlWeb/www/app.js','control?.TargetPlaytimeGoalsVersion','dynamic PTG version UI')
require('src/ControlWeb/www/app.js','control?.TargetPlaytimeGoalsCommit','dynamic PTG commit UI')
forbid('src/ControlWeb/www/app.js','0.5.0.0','stale hardcoded PTG version in UI')
forbid('src/ControlWeb/www/app.js','6d1679a9d9dc','stale hardcoded PTG commit in UI')
require('src/ControlWeb/www/app.js','asf?.BuildVariant','native ASF build variant for trim-safe runtime UI')
require('src/ControlWeb/www/app.js','asf?.MemoryUsage','native ASF memory for trim-safe runtime UI')
require('src/ControlWeb/www/app.js','parentalStatus','Family View UI')
require('src/ControlWeb/www/app.js',"password: ''",'IPC password starts only in page memory')
require('src/ControlWeb/www/app.js',"headers.set('Authentication', state.password)",'ASF auth header uses in-memory IPC password')
require('src/ControlWeb/www/app.js','sessionStorage.getItem(VIEW_KEY)','view preference restoration')
require('src/ControlWeb/www/app.js','sessionStorage.getItem(LOCK_KEY)','lock preference restoration')
require('src/ControlWeb/www/app.js','sessionStorage.setItem(VIEW_KEY','view preference persistence')
require('src/ControlWeb/www/app.js','sessionStorage.setItem(LOCK_KEY','lock preference persistence')
forbid('src/ControlWeb/www/app.js','PASSWORD_KEY','obsolete persistent IPC password identifier')
require('src/ControlWeb/www/app.js',"const LEGACY_IPC_STORAGE_KEY = 'asf.control.ipcPassword';",'legacy IPC password cleanup key')
require('src/ControlWeb/www/app.js','sessionStorage.removeItem(LEGACY_IPC_STORAGE_KEY);','legacy IPC password cleanup')
forbid('src/ControlWeb/www/app.js','sessionStorage.getItem(LEGACY_IPC_STORAGE_KEY)','legacy IPC password must never be restored')
forbid('src/ControlWeb/www/app.js','sessionStorage.setItem(LEGACY_IPC_STORAGE_KEY','legacy IPC password must never be persisted')
require('src/ControlWeb/www/app.js','Authentication','ASF auth header')
require('src/ControlWeb/www/app.js','/Api/ASF/Encrypt','native encryption')
require('src/ControlWeb/www/app.js','SteamPassword:encryptedPassword','encrypted password assignment')
require('src/ControlWeb/www/app.js','Core.applyPlaytimeConfig','PTG validated config builder')
require('src/ControlWeb/www/app.js','/Api/PlaytimeGoals/','PTG read integration')
require('src/ControlWeb/www/app.js','/Input','required input')
require('src/ControlWeb/www/app.js','/Api/ASF/${action}','native restart exit')
require('src/ControlWeb/www/app.js','startLockWatch','auto lock')
require('src/ControlWeb/www/core.js','GamesPlayedWhileIdle = []','single GamesPlayed owner')
require('src/ControlWeb/www/core.js','CustomGamePlayedWhileIdle = null','single custom idle owner')
require('src/ControlWeb/www/core.js','managed || game?.CanSelect','managed excluded removable')
require('src/ControlWeb/www/core.js','MAX_TARGET_HOURS','PTG max target')
require('src/ControlWeb/www/app.css','@media (max-width: 760px)','mobile layout')
require('src/ControlWeb/www/app.css','@media (prefers-reduced-motion: reduce)','reduced motion')
require('src/ControlWeb/www/app.css','.toast-region','toast styles')
require('src/ControlWeb/www/app.css','.full-account-row','desktop account action layout')
require('src/ControlWeb/www/app.css','dialog.modal','dialog styles')
require('src/ControlWeb/ControlWebPlugin.cs','public string WebPath => "/Control";','web path')
require('src/ControlWeb/www/index.html','/Control/i18n.js','i18n loaded')
require('src/ControlWeb/www/index.html','/Control/core.js','core loaded')
require('src/ControlWeb/www/index.html','/Control/qrcode.min.js','local QR renderer loaded')
require('installer/phone-transaction.sh','data-asf-control-suite-root="1"','default-root Control Suite entrypoint marker')
require('installer/phone-transaction.sh',"params.get('asfui') !== '1'",'legacy ASF-ui requires explicit bypass')
require('installer/phone-transaction.sh',"window.location.replace('/Control/' + window.location.search + window.location.hash)",'default-root redirect to Control Suite')
require('installer/phone-transaction.sh','ROOT_UI_INDEX="$ASF_ROOT/www/index.html"','stock ASF-ui entrypoint target')
require('installer/phone-rollback-core.sh','ROOT_UI_INDEX="$ASF_ROOT/www/index.html"','root UI rollback target')
require('src/ControlWeb/www/qrcode.min.js','QRCode','local QR renderer asset')
require('src/ControlWeb/www/qrcode.LICENSE.txt','QRCode for JavaScript','QR renderer license attribution')
require('src/ControlWeb/www/app.js','function accountDisplayName(','Steam persona primary identity helper')
require('src/ControlWeb/www/app.js','function nextBotName(','automatic technical ASF bot ID')
require('src/ControlWeb/www/app.js','QrChallengeUrl','native QR challenge rendering')
require('src/ControlWeb/www/app.js',"Type:QR_INPUT_TYPE, Value:'Y'",'native QR prompt acceptance')
require('src/ControlWeb/www/app.js','goalSort','playtime sort control')
require('src/ControlWeb/www/app.js','localeCompare','natural game-name sorting')
require('src/ControlWeb/www/app.js','legacyAsfHref','explicit legacy ASF-ui fallback helper')
require('src/ControlWeb/www/app.js','PERSONA_STATES','native Steam persona status options')
require('src/ControlWeb/www/app.js','next.OnlineStatus = status','native OnlineStatus persistence')
require('src/ControlWeb/www/app.js','id="onlineStatus"','per-account Steam persona selector')

require('src/ControlWeb/www/app.js','loadNativeConfigSchema','schema-driven native config editor')
require('src/ControlWeb/www/app.js',"ArchiSteamFarm.Steam.Storage.BotConfig",'full native BotConfig schema')
require('src/ControlWeb/www/app.js',"ArchiSteamFarm.Storage.GlobalConfig",'full native GlobalConfig schema')
require('src/ControlWeb/www/app.js',"'/Api/Command'",'native ASF command console')
require('src/ControlWeb/www/app.js',"'/Api/NLog/File?count=200'",'native ASF log viewer')
require('src/ControlWeb/www/app.js',"'/Api/IPC/Bans'",'native ASF bans')
require('src/ControlWeb/www/app.js',"'/Api/Plugins?official=true&custom=false'",'native plugin inventory')
require('src/ControlWeb/www/app.js',"'/Api/WWW/GitHub/Release/'",'native release information')
require('src/ControlWeb/www/app.js','GamesToRedeemInBackground','background redeemer')
require('src/ControlWeb/www/app.js','TwoFactorAuthentication','native 2FA tools')
require('src/ControlWeb/www/app.js','data-mass-bot','native mass editor')
require('src/ControlWeb/www/app.js','Emergency legacy ASF-ui','legacy UI only as emergency fallback')
require('src/ControlWeb/www/app.js','data-native-jump="bot-config"','account config routes into Control Suite')
require('src/ControlWeb/www/app.js','data-native-jump="2fa"','account 2FA routes into Control Suite')
require('src/ControlWeb/www/app.js','data-native-jump="bgr"','account BGR routes into Control Suite')
forbid('src/ControlWeb/www/app.js',"legacyAsfHref(`/bot/",'no per-account legacy ASF-ui links')





require('src/ControlWeb/www/app.js','formatGoalDuration','second-precision goal display')
require('src/ControlWeb/www/app.js','EffectiveSeconds','second-precision effective credit')
require('src/ControlWeb/www/app.js','RemainingSeconds','second-precision remaining time')
require('src/ControlWeb/www/app.css','.steam-avatar','Steam avatar styles')
require('src/ControlWeb/www/app.css','.qr-panel','QR onboarding styles')
require('src/ControlWeb/www/i18n.js',"ASF_LOCALE_KEY = 'asf-ui:locale'",'shared ASF-ui locale key')
require('src/ControlWeb/www/i18n.js',"'uk-UA'",'Ukrainian locale')
require('src/ControlWeb/www/i18n.js','Українська','Ukrainian catalog')
require('src/ControlWeb/www/i18n.js','const effectiveRequested = normalize(requested);','canonical locale alias display')
require('src/ControlWeb/www/i18n.js','safeStorageSet','locale persistence only')
require('src/ControlWeb/www/index.html','id="localeSelect"','app language selector')
require('src/ControlWeb/www/index.html','id="authLocaleSelect"','auth language selector')

require('scripts/build/prepare-release-worktree.sh','git -C "$PTG_REPO" archive','exact PTG archive export')
require('scripts/build/prepare-release-worktree.sh','"$PLAYTIMEGOALS_COMMIT"','canonical PTG commit used for export')
require('scripts/build/prepare-release-worktree.sh','PlaytimeGoals |','PTG source subtree export')
require('scripts/build/prepare-release-worktree.sh','"rollForward": "disable"','exact SDK roll-forward disabled')
forbid('scripts/build/make-release.sh','dotnet-install.sh','no remote SDK installer in release path')
forbid('scripts/build/make-release.sh','https://dot.net/','no remote SDK installer URL in release path')
forbid('scripts/build/make-release.sh','curl ','release builder performs no SDK download')
forbid('scripts/build/make-release.sh','wget ','release builder performs no SDK download')
require('scripts/build/make-release.sh','check-dotnet.sh','fail-closed exact SDK gate')
require('scripts/build/check-dotnet.sh','"$DOTNET_BIN" --list-sdks','exact installed SDK inventory')
require('scripts/build/check-dotnet.sh','DOTNET_SDK_VERSION','canonical exact SDK pin')
require('scripts/dev/bootstrap-dotnet-sdk.sh','dotnet-sdk.sha512','verified SDK hash manifest')
require('scripts/dev/bootstrap-dotnet-sdk.sh','builds.dotnet.microsoft.com','official SDK binary source')
require('scripts/dev/bootstrap-dotnet-sdk.sh','sha512sum','SDK integrity verification')
forbid('scripts/dev/bootstrap-dotnet-sdk.sh','dotnet-install.sh','no downloaded installer script')
require('scripts/build/build-release.sh','TreatWarningsAsErrors=true','warnings as errors')
for asset in ('index.html','i18n.js','core.js','qrcode.min.js','qrcode.LICENSE.txt','app.js','app.css'):
   require('scripts/build/build-release.sh',asset,f'ControlWeb build gate for {asset}')
require('scripts/build/package-release.sh','ControlWeb/www/i18n.js','locale asset staged for native ZIP')
require('scripts/build/package-release.sh','ControlWeb/www/qrcode.min.js','QR asset staged for native ZIP')
require('scripts/build/package-release.sh','ControlWeb/www/qrcode.LICENSE.txt','QR license staged for native ZIP')
require('installer/phone-transaction.sh','index.html i18n.js core.js qrcode.min.js qrcode.LICENSE.txt app.js app.css','locale + QR asset install gate')
require('scripts/build/package-release.sh','ASF-Control-Suite-v$CONTROL_SUITE_VERSION.zip','native bundle ZIP')
require('scripts/build/package-release.sh','AccountManager-v$CONTROL_SUITE_VERSION.zip','AccountManager native ZIP')
require('scripts/build/package-release.sh','ControlCenter-v$CONTROL_SUITE_VERSION.zip','ControlCenter native ZIP')
require('scripts/build/package-release.sh','ControlWeb-v$CONTROL_SUITE_VERSION.zip','ControlWeb native ZIP')
require('scripts/build/package-release.sh','PlaytimeGoals-v${PLAYTIMEGOALS_VERSION%.0}.zip','PlaytimeGoals native ZIP')
require('scripts/build/package-release.sh','CONTROL-SUITE-METADATA.json','external release metadata')
require('scripts/build/package-release.sh','SHA256SUMS','external artifact checksums')
require('scripts/build/package-release.sh','STAGE_ROOT','single canonical package stage')
require('scripts/build/package-release.sh','create-native-zips.py','canonical deterministic ZIP writer')
forbid('scripts/build/package-release.sh','.tar.gz','no transitional tar release')
forbid('scripts/build/package-release.sh','asf-control-suite-v1.0-dist','no transitional release name')
require('scripts/build/create-native-zips.py','ZipInfo','deterministic ZIP metadata')
require('scripts/build/create-native-zips.py','FIXED_ZIP_TIME','deterministic ZIP timestamp')
require('scripts/build/create-native-zips.py','sorted','deterministic ZIP member order')
require('scripts/build/verify-release-artifacts.py','SHA256SUMS','release checksum verification')
require('scripts/build/verify-release-artifacts.py','CONTROL-SUITE-METADATA.json','release metadata verification')
require('scripts/build/verify-release-artifacts.py','build -> bundle byte mismatch','build-to-bundle provenance gate')
require('scripts/build/verify-release-artifacts.py','build -> individual byte mismatch','build-to-individual provenance gate')
require('scripts/build/verify-release-artifacts.py','bundle -> individual byte mismatch','bundle-to-individual provenance gate')
require('scripts/build/package-release.sh','verify-release-artifacts.py','mandatory release provenance gate')
require('installer/phone-transaction.sh','ROLLBACK COMPLETE','automatic rollback')
require('installer/phone-transaction.sh','data["Headless"] = True','phone install enforces ASF headless mode for IPC QR onboarding')
require('installer/phone-transaction.sh','ASF_CONFIG_ABSENT','phone global config absence rollback marker')
require('installer/phone-transaction.sh','"$BACKUP/ASF.json"','phone global config transactional backup')
require('installer/phone-rollback-core.sh','"$BACKUP/ASF.json"','manual rollback restores phone ASF global config')
require('scripts/phone/phone-verify-via-adb.sh','data.get("Headless") is not True','phone verify checks headless invariant')
require('installer/phone-transaction.sh','Api/AccountManager','account health gate')
require('installer/phone-transaction.sh','Api/ControlCenter/Status','control OpenAPI gate')
require('installer/phone-transaction.sh','/Control/healthz','functional control health gate')
require('installer/phone-transaction.sh','control-suite-health','functional health sentinel gate')
require('installer/phone-transaction.sh','Control Suite health gate: root=$root control=$control health=$health swagger=$code','diagnostic health codes')
require('installer/phone-transaction.sh','Api/PlaytimeGoals','PTG health gate')
require('installer/phone-transaction.sh','CONTROL_PROC_ROOT','testable /proc process detection')
require('installer/phone-transaction.sh',"IFS= read -r -d '' argv0",'argv0-based ASF process detection')
require('installer/phone-rollback-core.sh',"IFS= read -r -d '' argv0",'rollback argv0-based ASF process detection')
require('scripts/phone/phone-verify-via-adb.sh',"IFS= read -r -d '' argv0",'verify argv0-based ASF process detection')
require('scripts/phone/phone-verify-via-adb.sh','/Control/healthz','phone verify functional control health gate')
require('scripts/phone/phone-verify-via-adb.sh','control-suite-health','phone verify health sentinel')
for process_file in ('installer/phone-transaction.sh','installer/phone-rollback-core.sh','scripts/phone/phone-verify-via-adb.sh'):
    forbid(process_file,'pgrep -x ArchiSteamFarm','truncated comm process detection')
require('scripts/phone/phone-install-via-adb.sh','phone-preflight-via-adb.sh','preflight before install')
require('scripts/phone/phone-install-via-adb.sh','phone-verify-via-adb.sh','verify after install')
require('scripts/phone/phone-rollback-via-adb.sh','phone-rollback-core.sh','manual rollback core')
require('src/ControlCenter/ControlCenterController.cs','ArbitraryHostCommands = false','host command safety')

app=text('src/ControlWeb/www/app.js')
if 'SteamPassword:steamPassword' in app or 'SteamPassword: steamPassword' in app:
    errors.append('plaintext Steam password assigned to BotConfig')
if re.search(r'window\.(?:alert|prompt|confirm)\s*\(',app):
    errors.append('browser alert/prompt/confirm remains in production UI')
if '<pre>' in app or 'JSON.stringify(status' in app or 'JSON.stringify(parental' in app:
    errors.append('raw status JSON remains in production UI')

for p in project_files({'.js','.html'}):
    try:t=p.read_text(encoding='utf-8')
    except UnicodeDecodeError:continue
    if 'localStorage' in t and p.relative_to(ROOT).as_posix() != 'src/ControlWeb/www/i18n.js':
        errors.append(f'persistent browser storage outside locale bridge in {p.relative_to(ROOT)}')
locale_js=text('src/ControlWeb/www/i18n.js')
if 'asf-ui:locale' not in locale_js or 'asf.control.ipcPassword' in locale_js:
    errors.append('locale bridge storage contract violated')
for token in ('Process.Start(','ProcessStartInfo','bash -c','sh -c','/bin/bash','/bin/sh','child_process','Runtime.getRuntime'):
    forbid_tree(token,'arbitrary shell/process execution')
ALLOWED_STATIC_URLS = ('https://avatars.akamai.steamstatic.com',)
for path in ('src/ControlWeb/www/index.html','src/ControlWeb/www/i18n.js','src/ControlWeb/www/app.js','src/ControlWeb/www/app.css'):
    candidate=text(path)
    for allowed in ALLOWED_STATIC_URLS: candidate=candidate.replace(allowed,'')
    if re.search(r'https?://',candidate,re.I): errors.append(f'external URL found in {path}')

patterns={
    'SteamID64':re.compile(r'\b7656119\d{10}\b'),
    'Tailscale CGNAT':re.compile(r'\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])(?:\.\d{1,3}){2}\b'),
    'GitHub token':re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    'private key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
}
for p in project_files():
    if p.name == 'static_contracts.py': continue
    try:t=p.read_text(encoding='utf-8')
    except UnicodeDecodeError:continue
    for label,pat in patterns.items():
        if pat.search(t):errors.append(f'{label} found in {p.relative_to(ROOT)}')

if errors:
    print('STATIC CONTRACTS: FAIL')
    [print(' -',e) for e in errors]
    sys.exit(1)
print('STATIC CONTRACTS: PASS')

# Release compile graph invariant: every ASF plugin project that participates in IPC/web build
# must explicitly expose Microsoft.AspNetCore.OpenApi as compile-only, matching ASF plugin guidance.
for project in (
    ROOT / "src" / "AccountManager" / "AccountManager.csproj",
    ROOT / "src" / "ControlCenter" / "ControlCenter.csproj",
    ROOT / "src" / "ControlWeb" / "ControlWeb.csproj",
):
    project_text = project.read_text()
    assert '<PackageReference Include="Microsoft.AspNetCore.OpenApi" IncludeAssets="compile" />' in project_text, project
