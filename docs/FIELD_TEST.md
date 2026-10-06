# Live field-test checklist after v1.0 installation

Installation success proves file integrity and plugin/API loading. It does not replace the Steam-behavior field test.

1. Authenticate at `/Control/` with the existing ASF IPC password.
2. Confirm Dashboard shows all accounts and four loaded modules.
3. Open each account workspace; verify lifecycle controls and RequiredInput if Steam asks for it.
4. Verify PlaytimeGoals library classification: OWN, FAMILY, FREE and EXCLUDED.
5. Save one finite goal and one unlimited goal; confirm reload reflects exact targets.
6. Use more selected games than batch size; confirm active batch and stable queued positions.
7. FREE: select a known unowned free game; verify pending/claim/retry behavior and ownership transition.
8. FAMILY: verify busy copy waits, then becomes eligible when the copy is available.
9. Start a real Steam game; PlaytimeGoals must stand down.
10. Start CardsFarmer; PlaytimeGoals must stand down and later resume.
11. With Family View writes enabled, verify temporary allows restore exact previous custom state.
12. Controlled ASF restart while temporary Family View state exists; recovery must finish before new idling.
13. Reconnect/config reload; verify no duplicate runner, stale GamesPlayed or unrecovered journal.
14. Leave it running across several refresh/reassert cycles and inspect for queue oscillation, repeated free-license claims or reconnect loops.

Immediate rollback triggers: ASF cannot reach root 200/API 401, `/Control/` or plugin routes disappear, RecoveryReady cannot return true, Family View recovery fails, real gameplay is fought, eligibility rules are violated, or free-license requests bypass the five-minute guard.


## RC2 regression

- Open Dashboard and System after authentication: both must load without HTTP 500.
- On the Mi Max 2 trimmed ASF runtime, disk telemetry may show `unavailable`; that is a supported state.
- Confirm Accounts metadata remains readable with the complete action set visible.
- If ASF-ui stores locale `uk`, ControlWeb must display `Українська` rather than an English-fallback debug label.

## RC4 startup regression

- Transactional install must reach IPC ready and `/Control/healthz` HTTP 200 without loading `ApiExplorerSettingsAttribute`.
- If IPC startup fails during MVC controller discovery, the installer must roll back automatically and live Steam tests must not begin.

## Accounts v2 / multi-account

Use a secondary/disposable Steam account for the first QR test. Do not disturb the existing working account until this flow passes.

1. Open `/Control/` → Accounts and confirm the existing account is labeled by Steam persona/avatar; `ASF ID: main` is secondary.
2. Add a new account in QR mode with the ASF bot ID field left blank. Confirm an `account-N` technical ID is allocated without a Steam login/password.
3. Confirm the local QR panel appears, scan it with Steam Mobile, approve the sign-in, and verify the card transitions to connected with SteamID/persona/avatar.
4. Add/switch between at least two accounts. Run Stop/Start/Pause/Resume on the secondary account and verify the existing account is unaffected.
5. Open Playtime Goals for each account and confirm the selector/persona label changes the exact BotName-backed API target. Do not save goals on the secondary unless intended.
6. Change game sorting between managed/name/hours/target/AppID/source and verify unsaved target values/checks remain intact.
7. Open Advanced and verify `/bots` is available only as the legacy stock ASF-ui fallback.
8. Repeat Accounts/Playtime smoke at mobile width and in `uk-UA`.
