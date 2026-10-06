# ASF Control Suite 1.0 — sandbox test report

Date: 2026-10-05

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

## Not claimable inside this sandbox

The sandbox does not contain `dotnet`, and direct binary download of the pinned SDK is blocked by the container network boundary. Therefore the exact C# compile against ASF 6.3.10.3 is still a mandatory build gate in `scripts/make-release.sh`. The script pins .NET SDK 10.0.400 and refuses to produce an install archive until all plugin builds pass with warnings as errors.

Real Steam/Family/Family View behavior is intentionally reserved for the live post-install test in `FIELD_TEST.md`.


## RC2 field regression

The first phone field test exposed a runtime-only `FileNotFoundException` for `System.IO.FileSystem.DriveInfo` inside `ControlCenterController.GetStatus()`. RC2 removes the hard assembly reference, resolves optional drive telemetry dynamically, and adds static/UI regression coverage so Dashboard/System remain healthy when storage telemetry is unavailable.

RC3 hardening: ControlCenter status avoids trim-unsafe RuntimeInformation/Architecture metadata and `/Control/healthz` now functionally exercises the same status builder for transactional install verification.

RC4 regression: a real-phone RC3 deployment correctly rolled back when IPC startup failed because the trimmed ASP.NET Core runtime lacked `Microsoft.AspNetCore.Mvc.ApiExplorerSettingsAttribute`. RC4 removes that optional MVC metadata attribute and adds a static regression guard while preserving the functional `/Control/healthz` gate.

## RC7 trimmed-runtime regression

- ControlCenter contains no direct `System.IO`, `Path`, `Directory`, or `DriveInfo` dependency.
- Storage fields remain in the API contract but report unavailable/null, so the existing UI unavailable-storage path is exercised without risking JIT-time missing-method failures.

## Accounts v2 live gates

Not claimable until the next exact phone build/install: real Steam Mobile QR approval, live challenge rotation, Steam persona/avatar population, and two-real-account action/Playtime scoping. RC7 remains the known-good live baseline until that candidate passes the transactional health gate.
