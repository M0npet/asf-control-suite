# Issue #36: synthetic ASF-only end-to-end rehearsal

This test is **strictly offline**, using a synthetic Boot snippet and mock tmux/curl.
No Android, ADB, Termux, Steam accounts, real tmux, PRoot, network IPC or
ASF runtime is accessed. The private Mi Max 2 candidate is **not used**.

The test runs the real candidate preparer against artificial boot text and
checks candidate file mode 0600. Then it copies that **synthetic** candidate
to a temporary mock HOME and runs the ASF-only launcher with fake session
state and fake HTTP responses. Fake tmux records an asf session only;
it **does not execute** the supplied Bash/PRoot command.

Assertions include unchanged proxy and Tailscale session IDs, creation
of one asf session, no forbidden binary execution, and refusal for
missing confirmation, incorrect hash, already-running ASF, and orphan IPC.

Run:

```sh
python3 tests/asf_only_synthetic_rehearsal.test.py
```

The repository sandbox suite includes the test.

Device-side read-only invocation audit found:
`TMUX_CREATE_LINE=PASS`, `TMUX_DETACHED=YES`,
`TMUX_NAMED_SESSION=YES`, `TMUX_WORKDIR_OPTION=NO`,
`DEBIAN_LOGIN=YES`, `NESTED_BASH_LOGIN=YES`,
`NESTED_BASH_COMMAND=YES`, `RESTART_LOOP=YES`,
`ASF_BINARY_REFERENCE=YES`, `SLEEP_IN_LOOP=YES`,
`CANDIDATE_SYNTAX=PASS`, `TMUX_AUDIT_READ_ONLY=PASS`.
These are text-based indicators, **not** proof of executable safety.

**Hard gate:** this rehearsal does not authorize installing, running, or
publishing the private on-device candidate. Before a live maintenance
window, obtain independent semantic review of the private candidate
and rehearse in a truly isolated Android/Termux/PRoot environment.
The guarded rollback --run remains disabled and PR #38 remains Draft.
