# ASF Control Suite 1.0 — verification report

Updated: 2026-10-07

## Passed

- Static architecture/security contract scan.
- Pure JavaScript PlaytimeGoals configuration unit tests.
- Real headless Chromium integration flow at desktop size (1440×1050).
- Real headless Chromium responsive smoke flow at mobile size (390×844).
- Stock ASF-ui locale bridge: preselected `uk-UA` and short `uk` alias are normalized to the visible Ukrainian option.
- ControlWeb language selector writes the exact same stock ASF-ui locale key.
- Ukrainian login, Dashboard, Accounts, Playtime Goals, Security, System and Advanced UI checks.
- Ukrainian desktop/mobile visual and horizontal-overflow checks.
- Login/authentication-header flow and tab-scoped credential clearing.
- RequiredInput submission.
- Steam persona/avatar primary identity with ASF BotName retained as secondary technical metadata.
- Multi-account switcher plus BotName-scoped workspace actions.
- Password/QR onboarding mode switch.
- Credential-free QR bot creation and native `QrCodeLogin` `Y` submission.
- Local QR renderer DOM output; no third-party QR service is used.
- QR asset attribution/license packaging contract.
- Playtime numeric-aware name sorting (`8AM` before `12 is Better Than 6`) and hours sorting.
- Playtime sorting does not refetch the library.
- Advanced exposes stock `/bots` only as a legacy fallback link.
- Account create with ASF AES ciphertext; plaintext is absent from persisted BotConfig.
- Account rename through modal flow.
- Destructive delete rejects wrong typed confirmation and accepts the exact account name.
- PlaytimeGoals finite/unlimited save, batch, parental flag and exact reload verification.
- OWN/FAMILY/FREE/EXCLUDED UI behavior; a new EXCLUDED row is disabled while a managed excluded row remains removable.
- Preservation of unrelated BotConfig/plugin settings while PlaytimeGoals keys are changed.
- Native ASF restart typed-confirmation flow.
- System UI gracefully renders unavailable storage telemetry instead of failing.
- Full account action rows preserve readable account metadata in desktop two-column layouts.
- No raw status JSON in the production UI.
- Basic accessible-name scan for visible interactive controls.
- Horizontal-overflow checks at desktop and 390 px mobile viewport.
- JavaScript syntax checks.
- Shell syntax checks for all build/install/rollback scripts.
- Fake-phone successful transactional install.
- Fake-phone manual rollback.
- Fake-phone forced post-swap failure and automatic rollback.
- Secret/private-address scan.

Screenshots produced by the Chromium suite are in `docs/screenshots/`.

## Exact build and release verification

The exact C# compile against ASF 6.3.10.3 passes with .NET SDK 10.0.400. The release pipeline requires the exact SDK, builds all plugin projects with warnings as errors, creates deterministic native ASF ZIP artifacts and runs release provenance verification.

The v1.0.0 candidate was additionally verified on the Mi Max 2 and published from the same deterministic CI artifact. Published provenance is pinned to Control Suite commit `15314163bfccd26207fe9c1e3a8504727fea2910`.

Final live acceptance confirmed:

- 72-second finite PlaytimeGoals scheduler target: PASS.
- PlaytimeGoals cleanup after completion: PASS.
- Steam Invisible persona configuration: PASS.
- Cold restart persistence/autologin: PASS.
- Control Suite as the default root UI: PASS.
- QR onboarding lifecycle: PASS.
- Transactional install, backup, verification and rollback path: PASS.

The native-ASF parity work added after v1.0.0 is regression-tested in CI but must not be described as part of the already-published v1.0.0 binary until a new candidate is field-tested and released.


## RC2 field regression

The first phone field test exposed a runtime-only `FileNotFoundException` for `System.IO.FileSystem.DriveInfo` inside `ControlCenterController.GetStatus()`. RC2 removes the hard assembly reference, resolves optional drive telemetry dynamically, and adds static/UI regression coverage so Dashboard/System remain healthy when storage telemetry is unavailable.

RC3 hardening: ControlCenter status avoids trim-unsafe RuntimeInformation/Architecture metadata and `/Control/healthz` now functionally exercises the same status builder for transactional install verification.

RC4 regression: a real-phone RC3 deployment correctly rolled back when IPC startup failed because the trimmed ASP.NET Core runtime lacked `Microsoft.AspNetCore.Mvc.ApiExplorerSettingsAttribute`. RC4 removes that optional MVC metadata attribute and adds a static regression guard while preserving the functional `/Control/healthz` gate.

## RC7 trimmed-runtime regression

- ControlCenter contains no direct `System.IO`, `Path`, `Directory`, or `DriveInfo` dependency.
- Storage fields remain in the API contract but report unavailable/null, so the existing UI unavailable-storage path is exercised without risking JIT-time missing-method failures.

## Post-v1.0.0 live gate

The v1.0.0 Accounts/QR path has completed live acceptance. New native-administration surfaces introduced after v1.0.0 remain gated from the next stable release until their exact phone candidate passes the same transactional install and live smoke process.
