# Accounts v2 implementation plan

1. Extend AccountManager summary with native Steam identity/QR fields: `AvatarHash`, `QrChallengeUrl`.
2. Add a local QR renderer asset to ControlWeb and package/install it with the rest of the web assets.
3. Add account identity helpers and account switcher UI.
4. Replace credential-only account creation with QR/password tabs; auto-generate technical bot IDs when omitted.
5. Add QR orchestration against native Bot API: create config, wait for RequiredInput 8, send `Y`, poll `QrChallengeUrl`, render and refresh locally.
6. Make workspace show Steam persona/avatar as primary and move ASF bot ID to technical metadata.
7. Keep all bot actions scoped by BotName and expose the useful `/bots` actions in workspace.
8. Add Playtime sort state/control and numeric-aware client-side sorting.
9. Add Advanced link to stock `/bots` as legacy fallback.
10. Extend uk-UA translations and responsive CSS.
11. RED: update static and Playwright integration tests first and confirm failure.
12. GREEN: implement until targeted tests pass.
13. REFACTOR/self-review: verify secrets, QR privacy, multi-account scoping, packaging, mobile, locale.
14. Run full sandbox suite and produce a user-applicable patch from live-green RC7 baseline.
