# Issue #36 — guarded rollback (experimental)

## Incident
The first guarded rollback attempt on Mi Max 2 stopped ASF after replacing the `asf` tmux session with HOLD, then aborted on `HOLD_SESSION_INVALID` before modifying the runtime. Subsequent replay of the tmux-formatted command failed to recover the service; the native Termux:Boot launcher and official phone verification later restored and validated the original accepted v1.1.0 candidate.

## Design requirements
- Never replay a captured tmux `pane_start_command`: it is not a shell-safe, round-trippable launcher.
- Use an independently verified HOLD marker on the tmux session and check that ASF is fully quiescent before modifying installed files.
- Verify the original backup using its checksum manifest; perform a read-only `--precheck` first.
- Restore the pre-install runtime, plugins, metadata and global config; compare restored bytes before releasing the guard.
- Recover via the native Termux:Boot launcher, wait for a new session and verify the ASF HTTP health gates.
- Do not auto-start from an ambiguous state or after partial file restoration; retain markers and require operator review.
- Record only fingerprints of the original launch command, never plaintext command contents.
- Require explicit typed authorization for `--run` in addition to approval of a field maintenance window.
- Protect the already accepted v1.1.0 candidate SHA and published GitHub Actions artifact from accidental rebuilding.

## Offline verification
An isolated v3 prototype and fifteen tests are available as a review patch in the project conversation. The tests cover precheck, HOLD setup failure, bad session ownership, failed restore, corrupted transfer, successful mock rollback, Termux:Boot failing to create a session, and protection against unintended live execution.

**Not approved for deployment.** The tests are mocked and not a substitute for a real Termux:Boot review or an isolated Android test. The tested 1.1.0 release candidate remains unchanged. CI must not consume exhausted GitHub Actions quota; commits on this development branch must use `[skip ci]` until the quota is available.

Tracks #36.
