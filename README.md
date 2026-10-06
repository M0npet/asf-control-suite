# ASF Control Suite v1.0 — source release

Modular control plane for the existing Mi Max 2 ASF setup. The release is pinned to:

- ArchiSteamFarm 6.3.10.3 — `27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad`
- ASF-ui — `2b36125533f41e624b2fdcdec44f37ad60c7daaa`
- PlaytimeGoals 0.5.0.0 — `fa959d3d4ffd09f7fd30e9ee8599aa5004b67033`
- Control modules 1.0.0.0
- .NET SDK build gate — 10.0.400

## Modules

- **PlaytimeGoals** — game-goal engine, queue, Steam Family, FREE auto-claim and Family View recovery.
- **AccountManager** — cross-bot summary with Steam persona/avatar/native QR challenge fields plus credential-free defaults.
- **ControlCenter** — safe runtime/module health; filesystem telemetry is deliberately reported as `unavailable` on the trimmed target instead of probing optional `System.IO` members; no shell executor.
- **ControlWeb** — unified `/Control/` UI with Steam-first multi-account management, native Steam QR/password onboarding, account-scoped PlaytimeGoals controls/sorting, and an ASF-ui-compatible locale bridge. Stock `/bots` stays available only as a legacy fallback.

See `docs/FUNCTION_MATRIX.md` for the complete implemented function list, `docs/INSTALL.md` for build/install/rollback, and `docs/FIELD_TEST.md` for the final live Steam test.

## Security / ownership

PlaytimeGoals remains the sole owner of its managed GamesPlayed and managed Family View state. ControlWeb never gets a shell surface. ASF IPCPassword stays authoritative; the browser keeps it only in sessionStorage and removes it on lock. New Steam passwords are encrypted by ASF AES before BotConfig persistence. The UI keeps scripts, styles, API traffic and QR generation local/self-hosted. CSP permits images only from self/data and the pinned Steam avatar host; QR challenge URLs are never sent to a third-party QR service. Language preference reuses the stock ASF-ui `asf-ui:locale` key; `uk-UA` is fully localized in ControlWeb and English remains the fallback.

## Deployment model

One exact release archive contains all four plugins. Phone installation is transactional: SHA verification → staging → backup → stop ASF child → plugin swap → byte verification → root/API/Control/OpenAPI health → success, otherwise automatic rollback.

Stock `/opt/asf/www`, the Termux `asf` supervisor, `asf-proxy` and `tailscale-watch` are not intentionally replaced or killed by the installer.

## Validation available in this sandbox

- static/security contracts
- pure JS configuration tests
- real Chromium UI integration test, including stock ASF-ui `uk-UA` auto-detection and shared locale persistence
- fake-phone successful install transaction
- fake-phone manual rollback
- fake-phone forced post-swap failure with automatic rollback
- JS and shell syntax
- secret/private-address scan

The only gate that cannot run in this sandbox is the exact C# compile because `dotnet` is not installed and the container cannot download SDK 10.0.400. `scripts/make-release.sh` makes that compile mandatory before an install archive is created.
