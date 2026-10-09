# Issue #36 — offline recovery hardening checkpoint (2026-10-10)

**Status:** Draft / experimental. This document is NOT authorization to deploy, install an adapter, execute `--start`, perform rollback, or touch production Mi Max 2 services.

## Verified development changes

- `asf-only-launcher.sh`: validate health retry settings before invoking an adapter; invalid settings cannot create a supervisor session.
- Replace `display-message -t '=name'` session-ID lookup with strict `list-sessions -F '#{session_name}|#{session_id}'` parsing. This aligns with the *previously field-observed Termux session-target/pane-target mismatch*. Malformed, absent, or duplicate required IDs fail closed. An initial snapshot failure now exits with `DEPENDENCY_ID_MISSING` (13), even under `set -e`.
- Probe the loopback ASF IPC without inherited HTTP proxies. Any actual HTTP response causes `ORPHAN_ASF_HTTP_LISTENER` (14); HTTP `000` **alone** does not permit startup. The probe must return **curl exit 7 plus HTTP 000** (failed TCP connection). Timeouts or other ambiguous errors produce `ASF_IPC_PROBE_INDETERMINATE` (24).
- Validate proxy and watcher identities again after the final successful HTTP health probes and check that the ASF session still exists before reporting `ASF_ONLY_LAUNCH=PASS`.
- `prepare-asf-only-adapter.sh`: replace ambiguous `mv -n` with an exclusive hardlink commit from a 0600 temporary file inside the same private directory. A competing destination produces `CANDIDATE_COMMIT_REFUSED` (18), not false success. This tool still **only prepares a review candidate**, never the active adapter.
- Extend repository regression test fixtures for alternate HTTP statuses, timeout/refusal distinction, malformed session IDs, proxy-session change during health checks, and candidate-output race.

## Offline execution evidence — explicitly limited

Two Bash scripts were reconstructed in an isolated local test directory, and their **Git blob SHA-1 hashes exactly matched** the GitHub branch contents:

| File | Exact blob ID |
|---|---|
| `scripts/phone/asf-only-launcher.sh` | `c51d31073a4bc89bf19a71e430bb8c998c111371` |
| `scripts/phone/prepare-asf-only-adapter.sh` | `bafce121bf062906ad171752ee7c987917538587` |

`bash -n` passed for both. A separate, locally constructed fake tmux/curl test harness ran **24 focused scenarios; all passed**, including an originally failing invalid-ID test that led to a subsequent correction. The harness used only temporary mock sessions and synthetic Boot text. It did not contact a real tmux server, ADB, Android, PRoot, Steam, Tailscale or any network endpoint.

**Limitations:** This is not a run of the repository's complete `tests/run-all.sh`, its original full test files, GitHub Actions or live Termux acceptance. Do not imply full-suite CI success. GitHub Actions were intentionally not dispatched.

## Open safety gates

1. Independently rerun **repository** offline tests and conduct review of the exact GitHub diff.
2. Validate the private device-specific nested Bash, PRoot and runtime environment without transferring secrets or running the production Boot script. A private candidate remains unapproved; lexical scans alone are insufficient.
3. Test real PRoot behavior only with a **disposable separate rootfs**, never with the production Debian rootfs. Isolated tmux worker acceptance does not provide PRoot isolation.
4. An ASF-only adapter can execute arbitrary trusted code: session-ID checks detect disruption **after the fact**. Before approval, inspect that exact adapter for direct and indirect auxiliary-service effects.
5. Confirm real Termux curl behavior for a refused loopback IPC, a hung listener, and session restart races in a scheduled, explicitly authorized acceptance window.
6. Keep `phone-guarded-rollback-v3.sh --run` **unconditionally blocked** (exit 40 before any ADB access), preserve baseline `main` SHA `6758b79ec17d17975e44aae3891de6a0f084b47e`, and never replay full Termux:Boot to recover ASF.

## Reference specifications

- tmux exact session names and session formats: https://github.com/tmux/tmux/blob/master/tmux.1
- curl exit status meanings: https://curl.se/docs/manpage.html
- GNU coreutils `mv -n` skip behavior: https://www.gnu.org/s/coreutils/manual/html_node/mv-invocation.html
- GNU hardlink creation: https://www.gnu.org/software/coreutils/manual/html_node/ln-invocation.html
