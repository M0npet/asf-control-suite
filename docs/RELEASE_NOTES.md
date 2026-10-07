# ASF Control Suite 1.1.0 — candidate notes

The `main` branch now targets **v1.1.0**. This candidate is not a stable release until the exact generated phone artifact passes the same live acceptance process used for v1.0.0.

## Native ASF parity

- Added a first-class Native ASF workspace for BotConfig/GlobalConfig administration, commands, Steam license add/remove, direct key redeem, inventory summary, Steam Points redemption, 2FA, IPC bans, plugin inventory, hashing/encryption utilities and safe bot-config copying.
- Background Redeemer is intentionally write-only in Control Suite so stored/redeemed Steam key contents are not fetched into the browser.
- ASF log history uses the native authenticated `/Api/NLog/File` endpoint; ControlWeb adds no filesystem-reading proxy/controller.
- Security-controlled BotConfig fields are hidden from the raw editor. `SteamTradeToken` is explicitly redacted from the browser editor, preserved on normal saves and stripped from copied bot configs.
- Raw BotConfig and mass-edit writes keep `GamesPlayedWhileIdle` empty while PlaytimeGoals is enabled, preserving a single GamesPlayed owner.
- Mass BotConfig edits snapshot originals and roll back already-applied bots if a later write fails.
- Fixed a delayed Steam-persona save rerender that could overwrite a freshly edited Native ASF textarea.
- Toast notifications no longer intercept pointer input for underlying controls; only the toast close button is interactive.
- Pinned deployment policy is enforced inside the native workspace: GlobalConfig saves keep ASF auto-update disabled, while generic `UPDATE`, `RESTART` and `EXIT` commands are blocked so process/update actions cannot bypass dedicated safety controls.
- CI locks these boundaries with browser integration, static contracts, exact pinned compilation and CodeQL.

## Release boundary

Stable **v1.0.0** remains pinned to Control Suite commit `15314163bfccd26207fe9c1e3a8504727fea2910`. v1.1.0 uses distinct package/version identifiers so development artifacts cannot collide with that published provenance.

---

# ASF Control Suite 1.0 — release notes

Control Suite 1.0 is the first polished release of the modular ASF control plane.

## RC2 field fixes

- Rebased the exact compatibility target to ASF 6.3.10.3 (`27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad`) and ASF-ui `2b36125533f41e624b2fdcdec44f37ad60c7daaa`.
- Fixed `ControlCenter/Status` crashing on trimmed ASF runtimes where `System.IO.FileSystem.DriveInfo` is absent. Storage telemetry is now optional and reports unavailable instead of returning HTTP 500.
- Added a regression contract that forbids a hard `DriveInfo` runtime dependency.
- Canonicalized ASF-ui's short `uk` locale alias to the visible `Українська` selector option.
- Fixed registered-account cards so action buttons no longer collapse account metadata on desktop two-column layouts.

## User interface

- Complete six-section UI: Dashboard, Accounts, Playtime Goals, Security, System and Advanced.
- Responsive desktop/tablet/mobile layout with a bottom navigation bar on narrow screens.
- Product dialogs replace browser `prompt()` / `alert()` flows.
- Typed confirmation is required for destructive bot deletion and ASF process actions.
- Toast notifications replace blocking browser alerts.
- Loading skeletons, explicit error/retry states, empty states and connection status are built in.
- Accessible labels/live regions/focus styles and reduced-motion support are included.
- Managed PlaytimeGoals status and Family View are rendered as structured cards/progress instead of raw JSON.
- Language selection is synchronized with the stock ASF-ui preference (`asf-ui:locale`).
- Ukrainian (`uk-UA`) is fully localized for ControlWeb with English fallback; no duplicate localization plugin is introduced.
- Locale behavior is verified on the login screen and all six ControlWeb sections, including desktop and mobile rendering.

## Account management

- Create, start, stop, pause, resume, rename and delete ASF bot accounts through native ASF endpoints.
- RequiredInput / Steam Guard values can be submitted from the account workspace.
- New Steam passwords are encrypted through native ASF AES before BotConfig persistence.
- Defaults for new bots remain credential-free and are recursively filtered server-side.

## PlaytimeGoals

- Search/filter the Steam library by OWN/FAMILY/FREE/EXCLUDED.
- Configure finite or unlimited targets, batch size and Family View writes.
- EXCLUDED games cannot be newly selected; already-managed excluded entries remain removable.
- Enabling PlaytimeGoals clears ASF native idle-game fields so there is one GamesPlayed owner.
- Save verifies the plugin reload reflects exact targets/settings before reporting success.

## Safety

- No arbitrary shell/process executor exists in browser-facing plugins.
- IPCPassword stays native ASF authentication and is kept only in page memory for the current authenticated document.
- Manual/inactivity lock clears the browser credential.
- Deployment remains out-of-band through the transactional ADB installer with persistent backup and rollback.

RC3 hardening: ControlCenter status avoids trim-unsafe RuntimeInformation/Architecture metadata and `/Control/healthz` now functionally exercises the same status builder for transactional install verification.

RC4 field fix: removed `ApiExplorerSettingsAttribute` from the functional `/Control/healthz` action. The trimmed linux-arm64 ASF runtime does not contain that optional MVC metadata type, which caused controller discovery to abort IPC startup before the health gate could run. The liveness action remains deliberately simple and functional, and a regression contract forbids the trim-unsafe attribute.

RC5 field fix: `/Control/healthz` no longer calls the trimmed-out `ControllerBase.Content(string, string)` helper. The probe now uses `Ok(object)`, an MVC helper already retained by ASF's own API controllers, returns a unique `control-suite-health` sentinel, and lets runtime exceptions surface as HTTP 500 for exact diagnostics. Installer/verification gates now validate that sentinel and report individual Control/health/Swagger status codes on failure.

RC6 field fix: removed every `Environment.*` dependency from `ControlCenter/Status` after the trimmed linux-arm64 runtime proved that even `Environment.Version` can be removed. Runtime/version/build-variant presentation now comes from ASF's native `/Api/ASF` response, while ControlCenter keeps only plugin/bot/module/storage telemetry that is required for its own health contract. A regression contract forbids reintroducing `Environment.*` into the status builder.

RC7 field fix: removed filesystem probing from ControlCenter entirely after the exact trimmed linux-arm64 runtime threw `MissingMethodException` for `System.IO.Path.GetPathRoot(string)` before the storage helper's try/catch could protect the endpoint. Status now reports storage as unavailable instead of touching `System.IO`; native ASF remains the source for runtime/build/memory data. Static contracts forbid direct `System.IO`, `Path`, `Directory`, and `DriveInfo` dependencies in ControlCenter.


RC8 field fix: phone deployments now enforce ASF `Headless=true` transactionally before the restarted runtime becomes healthy. The live QR regression showed that an interactive tmux launch lets the first bot block inside console `GetUserInput()`, so later bots can accept `/Api/Bot/.../Input` yet never advance to `LoginWithQrCode()` or publish `QrChallengeURL`. The installer now backs up the complete pre-install `config/ASF.json`, preserves all existing global settings while setting only `Headless`, restores the original file byte-for-byte on automatic or manual rollback, handles an initially absent global config, and the phone verification gate requires the headless invariant.


RC9 field fix: QR onboarding now stays inside the Add account card and updates in place instead of rerendering the entire Accounts view every poll. The browser keeps the retry lifecycle alive across failed Steam QR sessions and reconnects, re-accepts a fresh native QrCodeLogin prompt when ASF asks again, and replaces only the QR/status region when the Steam challenge actually changes. Ukrainian copy covers the idle, starting, reconnecting and connected states.


RC10 field fix: successful QR onboarding now stores the QR-derived Steam account name alongside ASF's native persistent session data in the bot database when UseLoginKeys is enabled. BotConfig stays credential-free, so QR completion does not itself trigger a config reload. On later BotConfig reloads (for example PlaytimeGoals changes), ASF restores the runtime SteamLogin from the bot database and can reuse the saved refresh token without falling into RequiredInput=Login. ControlWeb also exits the QR reconnect state when the bot stops or ASF requests a non-QR input, instead of polling forever behind a misleading reconnect message.
