# Issue #36 — guarded rollback v3 (experimental)

This operator-only script is not part of the accepted v1.1.0 release archive.
Do not deploy to the phone during development or run `--run` without a separate live-acceptance decision.

## Incident

The earlier v1 operator tool replaced the running `asf` tmux session with a HOLD and then incorrectly compared the tmux-formatted start command to `sleep 3600`. The guard validation failed and left the ASF process offline. Manual recovery via Termux:Boot eventually succeeded; the official phone verification passed, and the accepted v1.1.0 runtime remained unmodified.

## v3 changes

- HOLD ownership uses a tmux session option rather than comparing formatted start commands. All tmux session targets use exact `=name` matching, so an absent `asf` session cannot resolve to `asf-proxy`.
- Never replays the original supervisor command. Recovery uses the native Termux:Boot script and checks the session and HTTP separately.
- Records only SHA-256 fingerprints of the original startup command and working directory in Termux private cache.
- Verifies backup files, checksum manifest and local release artifact before any service interruption.
- On ambiguous state or a failure after mutation has started, fails closed with an explicit operator-required marker. `HUP`, `INT`, and `TERM` are handled by the same failure path as shell errors; forced termination or power loss still require manual recovery.
- `--run` requires `ASFC_LIVE_CONFIRMATION=I_ACCEPT_ASF_DOWNTIME` as an additional barrier, **not** proof of safety.
- Preserve the release candidate's SHA and provenance; do not rebuild/release until exact-candidate live acceptance is complete.

## Offline verification

`python3 tests/phone_guarded_rollback.test.py`

Mocks run entirely in local temporary directories, never using a live device. They test precheck, exact tmux session naming, signal interruption before and during mutation, guard ownership, Boot non-creation, failed transfer, failed restore, and normal mocked recovery. Real Termux/Android behavior is **not** validated by these tests.

## Verified Termux:Boot coupling — live-blocked

Sanitized, read-only review of the **actual Mi Max 2** boot script found three tmux service blocks:
- Lines 23–26: conditional creation of `asf`.
- Lines 42–45: conditional creation of `tailscale-watch`.
- Lines 68–74: the `asf-proxy` block checks/terminates the proxy session and creates it again.

Therefore the existing `boot_start_and_wait()` currently invokes a multi-service
launcher and can interrupt HTTPS/Tailscale access while trying to restore ASF.
A successful exit from the Boot script also does not guarantee ASF process health.
Until a **separate ASF-only launcher** is designed and verified, the top-level
`--run` mode is **unconditionally disabled before any ADB invocation** with
`ASF_ONLY_RECOVERY_REQUIRED` (exit 40). No environment-variable bypass exists.
The mocked rollback-body tests remain useful, but do not authorize execution.

## Remaining release gates

Independent operator review of actual Termux:Boot implementation without disclosing secrets, isolated Android/Termux rehearsal, review and approval for any live rollback, and full v1.1 checklist. Keep GitHub Actions disabled/skipped while quota is exhausted.
