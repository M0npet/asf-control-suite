# v1.0 self-review

The control plane has no arbitrary shell/process execution surface. OS-level deployment is deliberately out-of-band through explicit local ADB scripts, not callable from browser API routes.

Release construction uses exact committed PlaytimeGoals bytes (`git archive`) and an exact detached ASF worktree. The release archive is not produced until the exact C# build succeeds. The phone installer verifies archive hashes before mutation, creates a persistent preinstall backup, stages the new plugin tree, stops only the ASF child, swaps files, verifies installed hashes, and requires root 200, unauthenticated API 401, `/Control/` 200 and plugin routes present in OpenAPI. Post-swap failure invokes automatic rollback.

Sandbox review covers successful install, manual rollback and forced-failure automatic rollback against a fake ASF root; Chromium covers the browser runtime and critical API flows. Exact .NET compilation and real Steam behavior remain environment-specific gates rather than being claimed as sandbox-tested.


UI release review additionally covers desktop and 390 px mobile Chromium rendering, horizontal overflow, interactive-control accessible names, modal confirmation semantics, toast feedback, loading/error states and removal of raw runtime JSON. Visual smoke screenshots are stored in `docs/screenshots/`.

## Accounts v2 review

- Steam identity is presentation-only: `Nickname`/`AvatarHash` are primary in the UI while every native mutation still uses the explicit ASF `BotName` path parameter.
- QR onboarding does not introduce a new backend login mechanism. It creates a credential-free BotConfig, answers ASF's native `QrCodeLogin` input with `Y`, reads the authenticated `QrChallengeURL`, and renders it locally. No QR challenge is sent to a third-party service.
- Password onboarding still calls `/Api/ASF/Encrypt` before writing BotConfig; integration tests assert plaintext never reaches the persisted config object.
- The QR encoder is bundled locally. Its third-party license/attribution is shipped next to the asset.
- CSP remains self-only for scripts, styles and API traffic; the only added network exception is the exact Steam avatar image host.
- QR polling is scoped to the selected account, stops after connection/view change/session lock, and never changes another account's BotName/config.
- Playtime sorting is DOM-local after the library load, so changing sort order does not refetch the library or discard unsaved target/checkbox edits.
- Stock `/bots` is not modified and remains an Advanced/legacy fallback rather than a second primary account-management surface.
