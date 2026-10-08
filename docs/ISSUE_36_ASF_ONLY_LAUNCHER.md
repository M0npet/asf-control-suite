# Issue #36: isolated ASF-only launcher (experimental, NOT provisioned)

## Why this exists

Read-only analysis of the actual Mi Max 2 `~/.termux/boot/start-asf.sh` showed
three distinct tmux sections: the ASF supervisor (lines 23–36), Tailscale
watcher (around lines 42–54), and a proxy section (around lines 68–74) that
terminates and recreates `asf-proxy`. Re-executing the **entire** Boot script
as an ASF recovery mechanism is therefore unsafe for a control-plane endpoint.
Termux:Boot is a boot-time script runner, not an ASF-only restart API.

## Proposed separation

- `scripts/phone/asf-only-launcher.sh` is **Termux-local**, not a boot script.
- `--audit` reports session existence and adapter readiness. It is read-only.
- `--start` is opt-in; without an explicitly reviewed and SHA-256-pinned
  private adapter it exits before changing sessions. It must never be called
  from production until device-specific approval.
- The user-owned adapter path is fixed at
  `~/.config/asf/asf-only-session.sh`; this file is **not included** here.
  It must be derived from the actual, operator-reviewed ASF launch stanza,
  preserving original PRoot, user, working-directory and environment semantics.
  Do not infer it from tmux's `pane_start_command` and do not share secrets.
- Before executing, the launcher requires `ASFC_ONLY_ADAPTER_SHA256` (64 hex)
  equal to the private adapter SHA. It snapshots the adapter into a private
  temporary file, checks the *executed bytes* again, and removes the snapshot
  on normal and caught signal exits.
- It refuses to start if `asf` already exists (exact tmux matching), a proxy
  or watcher session is missing, the proxy/watch session ID is unobservable,
  or ASF HTTP already answers successfully while the tmux supervisor is absent.
- The pinned adapter is **trusted code**. The wrapper does not sandbox it; a
  malicious or incorrectly written adapter could still stop other services.
  Session ID comparison detects unintended restarts *after the fact* and is
  not a substitute for auditing the adapter before provisioning.
- The wrapper never executes `start-asf.sh`, evaluates tmux captured command
  strings, kills a tmux session, or modifies runtime/backup files.
- On success it requires the exact `asf` session, unchanged proxy and watcher
  session identities and root=200 / unauthorized `/Api/ASF`=401.
- On adapter failure or HTTP failure, it preserves the environment and
  returns an explicit error for operator review. It never retries recovery
  by deleting or relaunching other services.

## Current safety gate

**No on-device adapter has been created, reviewed or installed.**
There is no permission to perform a live `--start`, rollback, or boot-script
migration. The separate guarded rollback v3 `--run` remains unconditionally
blocked pending an accepted, isolated ASF-only restart path.

## Offline tests

`python3 -S tests/asf_only_launcher.test.py`

The tests use a synthetic, isolated tmux/curl/adapter implementation. They do
not run ADB, use network connections or touch any device. They check read-only
audit, explicit authorization, adapter pinning, exact session names,
existing-server refusal, missing dependencies, orphan API, successful mock
start, changed-proxy detection, failed adapter, health timeouts, private
snapshot deletion, and absence of Boot dependencies.

## Remaining acceptance gates

1. Conduct a **privacy-preserving, read-only** semantic audit of the real ASF
   launch block and all variables it depends on. Only names/line ranges and
   boolean findings should leave the device, never raw boot-script contents.
2. Construct the specific ASF-only adapter under human review, with no direct
   or indirect `asf-proxy` or `tailscale-watch` changes.
3. Rehearse on an isolated Termux/tmux/PRoot setup, verify credentials remain
   private and runtime options match the existing launcher.
4. Fresh code and safety review, tests, and separate operator approval before
   any planned live maintenance. Do not remove the guarded rollback hard stop
   before those gates have passed.
