# Issue #36 — Mi Max 2 isolated tmux rehearsal

## Scope

`asf-isolated-tmux-rehearsal.sh --run-synthetic` is a **non-destructive readiness rehearsal**, not a recovery tool. Its only runnable payload is an embedded, fixed Bash worker that writes a marker inside a temporary private directory and waits. The script does **not** execute or source the device's private adapter candidate, does **not** invoke `proot-distro` or `ArchiSteamFarm`, and does **not** install an ASF-only adapter.

A previous on-device read-only preflight reported Termux's Bash, tmux, PRoot, mktemp, sha256sum, timeout, and three live tmux sessions present, the candidate private/syntax-valid, no active adapter, and at least 64 MiB workspace free. That preflight did not run the candidate.

## Isolation contract

1. Explicit `--run-synthetic` required; no-arg/default mode declines before touching tmux.
2. Revalidate the private candidate (existence, regular non-symlink, mode 0600, owner, syntax) and absence of any installed active adapter.
3. Snapshot `asf`, `asf-proxy`, and `tailscale-watch` session IDs from the **default** tmux server, using exact `=name` targets.
4. Create a mode 0700 temporary directory under Termux `TMPDIR`. Create a brand-new tmux server exclusively through `tmux -S "$SOCKET"` with a socket inside that directory. Supply `-f /dev/null` at server creation to avoid inherited user tmux configuration. Never send a mutating command to the default tmux server.
5. Start only a generated safe Bash worker within that isolated tmux instance. Confirm its marker and session through the isolated socket. Its contents are fixed in the repository and do not include the private candidate, real PRoot, ASF, external network requests, secrets or identifiers.
6. Compare the three live tmux session IDs with their previous values, reporting only `UNCHANGED` or a fixed failure code; do not print values.
7. Terminate **only the isolated server** with its absolute socket and clean up private test files on both normal completion and failure paths.

## Limitations and remaining acceptance gates

This verifies only that a separate tmux instance and benign worker operate on the live Termux installation while the default tmux sessions remain unchanged. It does not verify production PRoot options, Debian working-directory semantics, auto-restart behavior, native ASF health or signal handling. It is **not** an execution rehearsal of the device-specific private adapter.

Mocked tests under `tests/asf_isolated_tmux_rehearsal.test.py` exercise success, missing prerequisites, altered live IDs, isolated launch errors, cleanup and nonexecution; they are not proof of behavior on Android. Run real tmux validation only with operator approval, review output, then separately plan further detached synthetic PRoot behavior if needed.

The GitHub branch remains Draft PR #38; production rollback `--run` remains disabled. Do not install an adapter, change boot scripts, stop any live session, or run the private candidate under this test.

## 2026-10-08 device finding and fix

An on-phone attempt returned `LIVE_ID=UNAVAILABLE` before creating the test socket. The script was querying `display-message -t`, which expects a pane target. The revised read-only snapshot uses `list-sessions -F` with exact session names and internal IDs. IDs, account names, and addresses are never printed. Run a new read-only device precheck before another isolated test. The live rollback remains disabled.
