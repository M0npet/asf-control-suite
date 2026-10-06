# Accounts v2 + multi-account control spec

Status: approved by user in chat on 2026-10-05.

## Goals

1. Make Steam identity the primary human-facing account identity everywhere in ControlWeb.
   - Primary label: Steam persona (`Nickname`) when available.
   - Secondary technical metadata: ASF bot ID (`BotName`) and SteamID.
   - Steam avatar when `AvatarHash` is available.
   - Never rename the ASF bot implicitly just because the Steam persona changes.

2. Make multi-account operation first-class.
   - One global selected ASF bot in ControlWeb.
   - Accounts and Playtime Goals expose a clear account switcher using Steam persona names.
   - All state-changing actions remain explicitly scoped to the selected bot ID.
   - Dashboard can aggregate all accounts.

3. Fold practical stock `/bots` functionality into `/Control/Accounts`.
   - start, stop, pause, resume
   - rename ASF bot ID
   - enable/disable bot config
   - delete bot
   - account status, Steam identity, authenticator and CardsFarmer state
   - required-input handling
   - link PlaytimeGoals for the selected account
   - legacy stock ASF-ui `/bots` remains available from Advanced as a fallback only.

4. Add onboarding modes.
   - QR code login (preferred): create an ASF bot without Steam credentials, start it, answer the native ASF `QrCodeLogin` prompt with `Y`, then render the native `QrChallengeURL` locally as a QR code and refresh it while ASF rotates the challenge URL.
   - Login/password: keep current native `/Api/ASF/Encrypt` flow and never write plaintext Steam passwords to BotConfig.
   - Internal ASF bot ID is optional in normal onboarding and auto-generated as `account-N`; it is shown as technical metadata, not as the account name.

5. Improve PlaytimeGoals list navigation.
   - Search and source filter stay.
   - Add explicit sorting: managed first, name A→Z, name Z→A, Steam hours descending/ascending, target descending/ascending, AppID ascending/descending, own first, family first.
   - Use numeric-aware locale name comparison.

## Security and architecture invariants

- No new shell/process execution endpoint.
- QR rendering is entirely local in ControlWeb. The Steam challenge URL must not be sent to a third-party QR service.
- AccountManager may expose only already-native runtime identity/status fields (`Nickname`, `AvatarHash`, `QrChallengeURL`) and must not store credentials.
- Password onboarding continues to use native ASF encryption before BotConfig write.
- QR onboarding uses native ASF Bot API + native `QrChallengeURL`; no ASF core patch.
- Existing RC7 trimmed-runtime protections remain unchanged.

## Exact ASF 6.3.10.3 behavior relied on

- `Bot` JSON exposes `Nickname`, `AvatarHash`, `QrChallengeURL`, `RequiredInput`, `SteamID`, and BotConfig.
- `ASF.EUserInputType.QrCodeLogin == 8`.
- When not Headless/Service, QR login first calls `RequestInput(QrCodeLogin, false)`; sending `Y` chooses QR.
- ASF then starts `BeginAuthSessionViaQRAsync`, publishes `QrChallengeURL`, updates it when the Steam challenge changes, and clears it after completion/cancellation.
- `/Api/Bot/{bot}/Input` supplies the requested input.

## UX acceptance criteria

- Existing `main` account renders as its Steam persona when `Nickname` is present; `ASF ID: main` is secondary.
- Account selectors render persona name first and still uniquely identify bot ID.
- QR onboarding can reach a visible local QR panel from a blank new account without requiring Steam login/password fields.
- QR panel automatically reflects a changed challenge URL.
- Password onboarding remains available and plaintext never reaches BotConfig.
- Playtime sorting can be changed without refetching the library.
- Stock `/bots` is linked only under Advanced/legacy fallback.
- Ukrainian locale covers all new visible strings.
- Desktop and mobile layouts have no horizontal overflow.
