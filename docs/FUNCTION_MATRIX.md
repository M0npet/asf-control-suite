# Final function matrix — v1.0

## PlaytimeGoals 0.5.2.0

- Finite target hours and unlimited (`null`) goals.
- Second-precision local deadlines and v1-minute-ledger migration to v2 seconds; Steam historical playtime remains minute-granularity.
- Batch scheduling (1..32) and stable queue position.
- OWN / FAMILY / FREE / EXCLUDED library semantics.
- Direct ownership takes priority over Steam Family metadata.
- Family-only games fail closed when availability is unknown and wait when all copies are busy.
- FREE selected games auto-request a free license with a five-minute retry guard.
- Real Steam gameplay has priority over PlaytimeGoals.
- ASF CardsFarmer has priority over PlaytimeGoals.
- Managed GamesPlayed ownership is isolated from native `GamesPlayedWhileIdle` / `CustomGamePlayedWhileIdle`.
- Optional Family View temporary allow policy with exact ABSENT/ALLOW/DENY restore and crash recovery journal.
- Status, Library and Parental APIs.

## AccountManager 1.0.0.0

- Cross-account summary.
- Global defaults for newly-created ASF bots.
- Cross-bot Steam identity summary (`Nickname`, `AvatarHash`, SteamID) and authenticated native QR challenge exposure (`QrChallengeURL`) for ControlWeb orchestration.
- 64 KiB defaults limit.
- Recursive removal of credentials, passwords, tokens, secrets and security-controlled fields.
- Does not own bot lifecycle or Steam credentials; lifecycle remains native ASF.

## ControlWeb 1.0.0.0

- Steam persona/avatar primary identity with ASF BotName retained as the technical ID.
- First-class multi-account switcher; lifecycle/config/Playtime actions remain explicitly scoped by BotName.
- Native Steam Mobile QR onboarding through ASF `QrCodeLogin` and `QrChallengeURL`; QR is rendered locally with no third-party QR service.
- Login/password onboarding remains available through native ASF encryption.
- PlaytimeGoals sorting: managed, numeric-aware name, Steam hours, target, AppID, own/family priority; sorting is client-side and preserves unsaved edits.
- Native ASF parity workspace is first-class inside ControlWeb: schema-driven full BotConfig and GlobalConfig editors, 2FA, background redeemer, Commands, Log, IPC bans, mass BotConfig editor, plugin inventory and release/update information.
- Per-account native Steam persona status is editable directly from ControlWeb, including Invisible.
- Stock ASF-ui is retained only as an emergency compatibility fallback behind the explicit `?asfui=1` bypass while the parity workspace is field-tested.

- Control Suite is the default UI at `/`; `/Control/` remains its canonical mount. The phone installer transactionally patches only `/opt/asf/www/index.html` as the default entrypoint and backs it up for exact rollback.
- Reuses the stock ASF-ui locale preference key `asf-ui:locale`; changing English/Ukrainian from ControlWeb updates the same preference.
- Full Ukrainian (`uk-UA`) localization for ControlWeb with English fallback; no separate localization plugin.
- Dashboard and multi-account workspace.
- Responsive desktop/tablet/mobile shell with narrow-screen bottom navigation.
- Product dialogs and non-blocking toast notifications; no browser prompt/alert.
- Loading skeletons, error/retry states and empty states.
- Structured managed-goal progress and Family View cards; no raw runtime JSON.
- Accessible labels/live regions/focus states and reduced-motion support.
- Add / start / stop / pause / resume / rename / delete accounts through native ASF APIs.
- RequiredInput / Steam Guard submission through native ASF API.
- New Steam passwords encrypted through native ASF AES before BotConfig persistence.
- Bot config enable/disable.
- Full PlaytimeGoals editor with search and source filters.
- Finite/unlimited targets, batch size and Family View-write settings.
- EXCLUDED rows cannot be newly selected; already-managed excluded/missing entries remain removable.
- Enabling PlaytimeGoals forces native idle fields empty so there is one GamesPlayed owner.
- IPCPassword kept only in page memory; refresh, inactivity lock, manual lock, logout and authentication rejection clear it.
- Strict self-only CSP, no external scripts/fonts/CDNs and no referrer leakage.
- Native ASF restart and exit with typed confirmation.
- No arbitrary host/shell command surface.

## ControlCenter 1.0.0.0

- Runtime health and target compatibility metadata.
- Bot/connection/farming/input summary.
- Managed memory plus runtime/module health. Filesystem total/free space is deliberately unavailable on the trimmed linux-arm64 target.
- Runtime OS/framework/architecture.
- Loaded module/version summary for all four modules.
- Explicit safety declaration: no shell execution and deployment stays out-of-band.

## Release / deployment system

- Exact source pins: ASF 6.3.10.3 + ASF-ui exact submodule + PlaytimeGoals exact commit.
- PlaytimeGoals exported from the exact Git commit, never from dirty working-tree bytes.
- Isolated detached ASF worktree.
- Exact .NET SDK 10.0.400 gate.
- Warnings-as-errors for all four plugin projects.
- Hash manifest for every deployable file.
- One release archive containing all four plugins and installer transaction logic.
- Read-only ADB preflight.
- ADB transfer checksum verification.
- Staging and pre-install backup before process stop.
- Only the ArchiSteamFarm child is stopped; the `asf` supervisor, proxy and Tailscale sessions are not intentionally killed.
- Post-install byte verification plus root/API/Control/OpenAPI health gates.
- Automatic rollback on post-swap failure.
- Persistent rollback backups and explicit manual ADB rollback.
- Read-only post-install verification, including installed-file hashes.
