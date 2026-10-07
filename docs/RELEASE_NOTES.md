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


RC10 field fix: successful QR onboarding now persists only the Steam account name learned from the native QR auth result when UseLoginKeys is enabled. ASF still keeps the password absent and stores the persistent refresh/access tokens in the native bot database. This prevents later BotConfig reloads (for example PlaytimeGoals changes) from falling into RequiredInput=Login and stopping the bot. ControlWeb also exits the QR reconnect state when the bot stops or ASF requests a non-QR input, instead of polling forever behind a misleading reconnect message.
