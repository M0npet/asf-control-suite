# Accounts v2 — next step from live-green RC7

RC7 is installed and healthy on the real Mi Max 2. The current source adds Steam-first identity, first-class multi-account controls, native QR onboarding, local QR rendering, Playtime sorting and a legacy `/bots` fallback link.

Next gate is an exact rebuild, not a manual DLL copy:

```bash
cd ~/Downloads/asf-control-suite-v1.0
bash tests/run-all.sh
bash scripts/make-release.sh ~/Downloads/ASF-6.3.9.6-src ~/Downloads/PlaytimeGoals-src
bash scripts/phone-preflight-via-adb.sh
bash scripts/phone-install-via-adb.sh artifacts/asf-control-suite-v1.0-dist.tar.gz
```

After install, verify `/Control/healthz` is 200, then test Accounts with a secondary Steam account through QR login before touching the existing account. Confirm Steam persona/avatar is primary, ASF ID remains secondary, switching accounts scopes actions/goals correctly, and Playtime sorting does not lose unsaved form state.

Hard gate: if the exact build or transactional health gate fails, do not copy partial files manually. Use the emitted stack/rollback diagnostics and fix the root cause first.
