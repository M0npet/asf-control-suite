# v1.1 live acceptance checklist

This checklist is the mandatory field gate between a green CI candidate and a stable ASF Control Suite release.

## Candidate identity

Before installing anything, record all four values from the exact CI run:

- Control Suite commit SHA
- GitHub Actions run ID
- retained artifact ID
- SHA-256 of `asf-control-suite-v1.1.0-dist.tar.gz`

The candidate is invalid if any of these values changes during testing.

## Preflight

- Existing ASF installation is healthy before the transaction.
- Persistent rollback backup is created successfully.
- Current global ASF config, bot configs and databases remain outside the candidate archive.
- Phone candidate checksum matches the retained CI artifact.
- Installer preflight reports the expected linux-arm64 layout.
- No plaintext IPC password, Steam password, login key, Family View PIN, SteamTradeToken, TLS key or runtime database is present in the candidate.

## Transactional installation

- ADB transfer checksum matches the local candidate.
- Installer stages and verifies all files before process stop.
- Only the ArchiSteamFarm child process is replaced.
- ASF restarts successfully with `Headless=true`.
- `/` opens Control Suite.
- `/Control/healthz` returns the expected Control Suite sentinel.
- native ASF API and Swagger/OpenAPI health checks pass.
- installed-file hashes match the candidate manifest.

## Existing v1.0 regression smoke

These must remain green after installing v1.1:

- IPC authentication works and the password remains page-memory-only.
- Refresh requires reauthentication.
- QR onboarding completes and survives a later BotConfig reload.
- Password onboarding encrypts the Steam password before persistence.
- account start/stop/pause/resume/rename/delete work.
- RequiredInput submission works.
- Steam persona `Invisible` persists.
- PlaytimeGoals finite target works with second-precision local deadline.
- completed goals clean up correctly.
- FREE/FAMILY/EXCLUDED handling remains correct.
- cold restart restores the existing login/session.
- default root Control Suite UI survives restart.

## New v1.1 Native ASF workspace

Test against real ASF state, not mocks:

- BotConfig editor loads and saves a harmless field.
- hidden BotConfig secrets never appear in the editor.
- `SteamTradeToken` is not rendered and remains unchanged after a normal save.
- GlobalConfig editor omits IPC/license/proxy secrets and a harmless setting can be saved without losing them.
- PlaytimeGoals-enabled BotConfig saves keep `GamesPlayedWhileIdle=[]` and `CustomGamePlayedWhileIdle=null`.
- command console executes a harmless read-only ASF command.
- generic command console rejects `UPDATE`, `RESTART` and `EXIT`.
- Background Redeemer accepts a disposable test key or a safely invalid key without reading existing stored key material into the browser.
- Steam license add accepts a harmless/free app or package ID on a disposable account; removal is tested only on a disposable license and requires the `REMOVE LICENSES` typed confirmation.
- direct key redeem accepts a safely invalid/disposable key and renders ASF's native result without persisting it in browser storage.
- inventory summary loads through native `/Api/Bot/.../Inventory`; a known AppID/ContextID can also load item data through the native detailed inventory endpoint without adding a filesystem proxy.
- Steam Points redemption is tested only on a disposable/test account and requires the `REDEEM POINTS` typed confirmation.
- 2FA token display works on an account with an authenticator.
- confirmation listing works; accept/decline is tested only if a safe disposable confirmation exists.
- authenticator import/delete is not tested destructively on a valuable account unless a dedicated test account is available.
- IPC bans view and single unban work when a disposable test ban is available.
- native NLog history loads through `/Api/NLog/File`.
- plugin inventory loads.
- hash/encrypt helpers return native ASF results.
- bot-config copy creates a disabled, credential-free copy and does not copy `SteamTradeToken`.
- mass editor updates multiple disposable bot configs.
- induced partial mass-edit failure rolls back already-applied configs.

## UI and mobile smoke

- desktop layout has no horizontal overflow.
- 390 px mobile layout has no horizontal overflow.
- Native ASF workspace is usable on the phone.
- toast overlays do not block underlying controls.
- Ukrainian locale remains selectable and persistent through the ASF-ui locale key.
- explicit legacy ASF-ui fallback still opens when requested.

## Rollback acceptance

Perform at least one controlled rollback test with the exact candidate:

- manual rollback restores the previous runtime/plugins/root UI.
- pre-install global ASF config is restored byte-for-byte.
- existing bot configs and databases remain intact.
- rollback restarts the prior ASF successfully.
- root UI and health endpoint return to their previous state.

## Release authorization

A stable release may be published only when:

1. CI and CodeQL are green for the exact candidate commit.
2. the exact-build artifact is still retained by GitHub Actions.
3. every applicable item above is PASS or explicitly marked NOT APPLICABLE with a reason.
4. the tested phone archive SHA-256 is recorded.
5. `.github/workflows/publish-release.yml` is invoked with that exact commit, artifact ID and accepted phone SHA-256.
6. the workflow verifies `CONTROL-SUITE-COMMIT.txt`, `SHA256SUMS` and the accepted phone hash before creating the tag/release.

Do not rebuild after live acceptance. If code, pins, packaging or the candidate bytes change, restart the acceptance cycle with the new exact artifact.
