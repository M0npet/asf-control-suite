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

## Phase 2: 2026-10-10 independent exact-source regression

A subsequent hardening pass (on the same PR branch) addressed:

- **ASF supervisor identity:** snapshot the newly created `asf` tmux session ID and verify it remains unchanged both during polling and immediately before success. A session replaced during HTTP readiness must not be accepted.
- **Shell injection in private candidate:** reject both `$(...)` and backtick substitutions during candidate preparation, prior to any candidate write.
- **Duplicate launch on one line:** count occurrences of `tmux new-session`, not merely lines containing that string.
- **Adapter path aliases:** canonicalize both candidate and active adapter paths using `realpath -m` so `../` components or symlinked parents cannot bypass the executable-adapter write exclusion. If canonicalization support is absent, the preparer fails closed.
- Add targeted repository regression fixtures for the ASF ID race, unsafe substitutions, duplicate inline tmux operations and canonical path aliases.

**Independent local execution (not GitHub Actions):** two exact Bash source files were transferred into an isolated Linux test directory, and `git hash-object` confirmed that their byte content matched the live GitHub branch blobs. `bash -n` passed both files. A separate fake tmux/curl/Boot harness exercised **36 focused scenarios: 36 PASS** (19 launcher cases and 17 preparer cases), including refusal, timeout, session replacements, malformed IDs, private output, secret suppression and path alias rejection.

Verified exact Git blob IDs at this checkpoint:

| File | Blob SHA-1 |
|---|---|
| `scripts/phone/asf-only-launcher.sh` | `5d524e49b05c77717ff9587e3bd45e1aac886e74` |
| `scripts/phone/prepare-asf-only-adapter.sh` | `8e654465d7338fd5111f14d86ea89abab83b8568` |

These **36 checks are independent focused tests**, not execution of the repository's own full `tests/run-all.sh` or its complete original test modules. They are intentionally device-independent. They prove neither the safety of an unreviewed private adapter nor compatibility with Mi Max 2 Termux/PRoot. No GitHub Actions, real network, ADB, rootfs or installed ASF process was used.

### Remaining gates and exact boundaries

- Keep v3 rollback `--run` unconditionally blocked. Its historical test-only body still contains a full Boot replay path and MUST NOT be field executed.
- Validate the new candidate checks under the installed Termux toolchain, particularly `realpath -m` and curl's refused-socket behavior, before deploying preparer changes.
- Do **not** treat `proot-distro login --isolated` as a clone of the Debian rootfs: it excludes selected host mounts but retains the same container root filesystem. Future execution testing requires a separately created, disposable rootfs, independent of production.
- A trusted adapter is arbitrary shell code. An AST/semantic review and separate user-approved field rehearsal must precede any production restart.
- Full repository tests and a PR diff review with separate approval are still needed; maintain Draft and do not merge/release.

## Phase 3: Dormant rollback recovery refactor (2026-10-10)

After the 36 independently verified launcher/preparer checks above, the experimental v3 rollback source and its repository mock tests were refactored further:

- Removed the dormant `boot_start_and_wait()` replay of the *multi-service* Termux:Boot script.
- Added future-only private ASF-only launcher and adapter SHA-256 preflight before any supervisor stop, with exact regular-file and Bash syntax checks.
- After invoking the privately pinned launcher, independently require the exact `asf` tmux session to exist.
- Made HOLD pane inspection use `tmux list-panes` rather than `display-message` target-pane resolution; expanded corresponding fake-tmux regression assertions.
- Added source-contract tests to prevent reintroduction of the full Boot replay and to check the sequence of safety gates.
- Added a one-command offline developer harness: `bash scripts/phone/issue36-offline-check.sh`. It runs five repository test modules and Bash syntax checks without ADB/phone contact.

**Execution limit:** these latest rollback refactor tests and the new one-command repository harness have been added but **NOT independently executed** against the complete current branch in this environment. The separately verified 36/36 checks are still valid for the two unchanged launcher/preparer source blobs only. No live change, merge, release, rootfs execution, GitHub Actions dispatch, or phone service interruption occurred.

The v3 `--run` entrypoint continues to return exit 40 before ADB with no bypass. A human-approved, byte-pinned private adapter is still missing; no existing test substitutes for Android/PRoot acceptance. 

## Phase 4: Exact remote rollback-body synthetic execution (2026-10-10)

A further independent isolated local rehearsal reconstructed the **exact executable remote Bash body** from the current GitHub `phone-guarded-rollback-v3.sh` here-document (`<<'PHONE'`). The 11,661-character fragment matched the current GitHub body length and FNV-1a/32 fingerprint `1ae69328`, and `bash -n` passed. (Unlike the launcher/preparer checks above, this is a body-level match, not a full-file Git blob equivalence proof.)

Using entirely synthetic temporary state and fakes for `tmux` and `proot-distro`, **17/17 focused inner-body scenarios passed**, including precheck without changes, successful mock rollback, no full-Boot replay, corrupted/missing launcher or adapter pins, invalid backup/core, lost ASF, failed HOLD creation, unexpected pane type, guard ownership corruption, restoration failure, failed reappearance after a nominal launcher exit, and pre-hold interruption recovery.

**Independent combined local result: 53/53 PASS** — 19 launcher cases + 17 preparer cases + 17 rollback-body cases. This is **not** a successful full repository suite. It does **not** exercise real PRoot or Android or prove a real device adapter is safe. It also does not run the full outer ADB host path; the top-level live `--run` remains unconditionally blocked before ADB, as source-inspected.

Current rollback GitHub blob SHA-1 at this checkpoint: `c9293bf153dc081097cda7e04c1fec133d7c0ee3`.

Still mandatory before merge or real operation: run the repository-native offline modules and complete `tests/run-all.sh`, isolated disposable-rootfs PRoot acceptance, private device-specific adapter review, real on-phone smoke tests with explicit authorization, and successful controlled rollback field acceptance.
