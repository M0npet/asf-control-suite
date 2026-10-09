# Issue #36 — guarded rollback v3 (experimental)

This operator-only script is not part of the accepted v1.1.0 release archive.
Do not deploy to the phone during development or run `--run` without a separate live-acceptance decision.

## Incident

The earlier v1 operator tool replaced the running `asf` tmux session with a HOLD and then incorrectly compared the tmux-formatted start command to `sleep 3600`. The guard validation failed and left the ASF process offline. Manual recovery via Termux:Boot eventually succeeded; the official phone verification passed, and the accepted v1.1.0 runtime remained unmodified.

## v3 changes

- HOLD ownership uses a tmux session option rather than comparing formatted start commands. All tmux session targets use exact `=name` matching, so an absent `asf` session cannot resolve to `asf-proxy`.
- Never replays the original supervisor command or runs multi-service Termux:Boot. Dormant recovery now uses a separate, SHA-pinned private ASF-only launcher, and independently verifies the restored exact `asf` session.
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

The former `boot_start_and_wait()` function was removed from the experimental branch. Its replacement requires the privately approved, pinned ASF-only launcher and adapter, both verified before stopping ASF. The installed Termux:Boot file is only inspected read-only. The top-level `--run` remains unconditionally disabled before any ADB invocation (`ASF_ONLY_RECOVERY_REQUIRED`, exit 40), with no bypass. The experimental mock tests do not authorize live recovery.

## Remaining release gates

Independent operator review of actual Termux:Boot implementation without disclosing secrets, isolated Android/Termux rehearsal, review and approval for any live rollback, and full v1.1 checklist. Keep GitHub Actions disabled/skipped while quota is exhausted.


## 2026-10-10 gated recovery refactor

The dormant recovery helper no longer executes the multi-service Boot script. Before any hold/mutation, it now checks the independently approved SHA-256 hashes and syntax of a fixed private ASF-only launcher and device adapter. Neither is provisioned by this PR. The top-level live rollback remains blocked before ADB. The complete repository regressions and Android field acceptance are outstanding.
