# ASF Control Suite v1.0 — READY FOR BUILD + INSTALL

## Release identity

- ASF: 6.3.10.3
- ASF source: `27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad`
- ASF-ui: `2b36125533f41e624b2fdcdec44f37ad60c7daaa`
- PlaytimeGoals: 0.5.0.0
- PlaytimeGoals source: `fa959d3d4ffd09f7fd30e9ee8599aa5004b67033`
- AccountManager / ControlCenter / ControlWeb: 1.0.0.0
- Required build SDK: .NET 10.0.400

## Ready

### PlaytimeGoals
- finite and unlimited targets
- batch 1..32 and queue positions
- OWN / FAMILY / FREE / EXCLUDED classification
- own-game priority over family metadata
- family-copy availability and fail-closed unknown state
- FREE license auto-claim with five-minute retry guard
- real gameplay priority
- CardsFarmer priority
- isolated GamesPlayed ownership
- optional Family View temporary allow / exact restore / crash journal recovery
- status, library and parental APIs

### AccountManager
- cross-account summary with Steam persona, avatar hash and native QR challenge URL
- credential-free defaults for new accounts
- recursive secret-field filtering
- 64 KiB defaults limit
- lifecycle and credentials remain owned by native ASF

### ControlWeb
- independent `/Control/` interface; stock ASF-ui stays untouched and `/bots` is linked only as a legacy fallback
- Steam persona/avatar is primary identity; ASF BotName is secondary technical ID
- first-class multi-account switcher and account-scoped actions
- add/start/stop/pause/resume/rename/delete via native ASF API
- RequiredInput / Steam Guard submission
- preferred native Steam Mobile QR onboarding using ASF `QrCodeLogin` + `QrChallengeURL`, rendered locally
- password onboarding remains available; new-account Steam password is encrypted by native ASF AES before persistence
- enable/disable bot config
- full account-scoped PlaytimeGoals editor
- explicit numeric-aware sorting (managed/name/hours/target/AppID/source) without refetching the library
- finite/unlimited targets, batch and Family View writes
- EXCLUDED cannot be newly selected; existing excluded goals remain removable
- enabling PlaytimeGoals clears native idle fields to preserve one GamesPlayed owner
- IPC password only in sessionStorage
- manual lock + inactivity lock
- typed confirmation for destructive actions
- native ASF restart/exit
- CSP keeps scripts/styles/API/QR self-hosted; only the pinned Steam avatar image host is allowed externally
- no shell/host command surface
- stock ASF-ui locale bridge via `asf-ui:locale`; no separate localization plugin
- full `uk-UA` ControlWeb catalog with English fallback
- language selector on login and authenticated UI, synchronized with stock ASF-ui preference

### ControlCenter
- runtime and compatibility health
- bot connectivity/farming/input summary
- managed memory plus bot/module/runtime health; native ASF supplies version/build/runtime presentation
- filesystem telemetry explicitly unavailable in-process on the trimmed linux-arm64 target
- loaded control-module versions
- no shell executor

### Build / deployment
- exact detached ASF worktree
- exact ASF-ui revision verification
- exact committed PlaytimeGoals export
- .NET 10.0.400 hard gate
- warnings-as-errors for all four plugins
- deployable-file SHA256 manifest
- read-only ADB preflight
- local + ADB archive checksum verification
- staging before mutation
- persistent pre-install backup
- stops only ArchiSteamFarm child; supervisor/proxy/Tailscale are not intentionally killed
- plugin-only swap; stock `/opt/asf/www` untouched
- installed-byte verification
- root/API/Control/OpenAPI health gate
- automatic rollback on failed install
- explicit manual rollback
- read-only post-install verification

## Verified in sandbox

- static/security contracts: PASS
- PlaytimeGoals config/core JS tests: PASS
- Chromium UI integration: PASS (desktop + mobile + `uk-UA` locale bridge)
- successful fake-phone transaction: PASS
- manual fake-phone rollback: PASS
- forced post-swap failure + automatic rollback: PASS
- JavaScript syntax: PASS
- shell syntax: PASS
- secret/private-address scan: PASS

## Accounts v2 gates that must happen outside this sandbox

RC7 is already live-green on the Mi Max 2 (`root=200 api=401 control=200 health=200 swagger=200`). The current Accounts v2 source is based on that RC7 baseline and must now pass:

1. Exact C# compile against pinned ASF 6.3.10.3 / .NET SDK 10.0.400.
2. Transactional install on the Mi Max 2 with the existing functional `/Control/healthz` rollback gate.
3. Live QR onboarding test with a disposable/secondary Steam account: create credential-free bot → native `QrCodeLogin` prompt → local QR → Steam Mobile approval → connected persona/avatar.
4. Live multi-account test: two accounts visible by Steam persona, switch workspace/goals independently, actions remain scoped to the correct ASF BotName.
5. Playtime sorting/filtering smoke test plus desktop/mobile/uk-UA review.
6. Whole-branch review and explicit release/tag decision.

No final v1.0.0 release is claimed until those gates are completed.

### Trimmed-runtime field history

RC3–RC7 progressively removed MVC/runtime/filesystem members absent from the phone's trimmed runtime. RC7 is the confirmed live baseline: ControlCenter health is 200 and filesystem telemetry intentionally reports unavailable. Accounts v2 does not change those RC7 ControlCenter protections.
