# Issue #36: ASF-only adapter candidate preparer (EXPERIMENTAL)

This utility helps an operator extract the existing ASF supervisor **command text** from an already audited Mi Max 2 Termux:Boot script **without executing it**. It is not a deployment or rollback tool.

## Why not copy all of Termux:Boot?

The actual boot script has an ASF stanza around lines 23–36, a Tailscale session, and a proxy stanza that stops and recreates `asf-proxy`. Running the entire boot file to restart ASF can interrupt the HTTPS control plane. Official Termux:Boot only specifies boot-time script execution; it is not an independent service restart API.

## Modes

- `--audit` (default): reads the boot file, checks its syntax and a strictly anchored snippet from original lines 26–34, and prints **fixed-vocabulary status codes and the ending line number**. It does not create a file or execute tmux, Debian or ASF.
- `--prepare`: performs the same checks, then privately writes a candidate to `~/.cache/asf-control-suite/candidates/asf-only-session.candidate.sh` with mode `0600`. It never writes to `~/.config/asf/asf-only-session.sh`, never executes the candidate, and does not change any tmux session.
- Neither mode prints the boot script, any code fragment, IP, credentials, values or user paths. Failed Bash parsing errors are suppressed to avoid exposing source.

## Fail-closed limitations

The preparer assumes the **known** layout: a tmux check at line 23, a `tmux new-session` at line 26, PRoot at line 28 and ASF at line 30. It finds the first Bash-syntax-complete candidate up to line 34, rejects auxiliary service names, suspicious tmux commands and nonliteral session names. Layout/quoting mismatches stop the attempt.

**This is only lexical and syntax validation, not evidence that the extracted launch command is safe or complete.** Bash source can have side effects or dependencies not discoverable by string search. The result may depend on variables/functions/environment outside the extracted span. It must undergo local, independent semantic review and a detached synthetic tmux/PRoot rehearsal before it can be moved to the fixed adapter path, pinned by SHA-256 or invoked by `asf-only-launcher.sh`.

No adapter is provisioned by this tool. The live rollback `--run` remains unconditionally disabled in PR #38. Do not run either adapter nor rollback on Mi Max 2 during this development phase.

## Offline testing

Run `python3 tests/prepare_asf_only_adapter.test.py` against mocked Boot text and filesystem. Tests prove that the **preparer** does not execute Boot code or change sessions. No Android, ADB, Termux or live credentials are required. These are *not* live acceptance tests.


## Field review: private candidate static dependencies

The private candidate on Mi Max 2 was produced from the audited original Boot
stanza (lines 26–33) **without execution**. The device returned:
`CANDIDATE_FILE=PASS`, `FILE_PERMISSIONS=PASS` (0600),
`FILE_OWNER=PASS`, `CANDIDATE_SYNTAX=PASS`,
`CANDIDATE_HASH_READABLE=PASS`, `MATCHES_ORIGINAL_BOOT=PASS`,
`ACTIVE_ADAPTER=NOT_INSTALLED`, `VERIFICATION_READ_ONLY=PASS`.

Further device-local read-only lexical review returned:
`ENV_VARIABLE_REFERENCES=NO`, `COMMAND_SUBSTITUTION=NO`,
`INDIRECT_EXPANSION=NO`, `SOURCED_SCRIPTS=NO`,
`DYNAMIC_EVAL=NO`, `AUXILIARY_REFERENCES=NO`,
`DESTRUCTIVE_TMUX=NO`, `NESTED_BASH=YES`,
`SINGLE_TMUX_CREATE=PASS`, `CANDIDATE_SYNTAX=PASS`,
`ACTIVE_ADAPTER=NOT_INSTALLED` and
`DEPENDENCY_REVIEW_READ_ONLY=PASS`.

This is **lexical evidence only**, not a Bash AST review or an
execution-safety guarantee. In particular, nested shell quoting, inherited
Termux environment, PRoot options and hidden runtime side effects have not
been proven safe. Do not copy candidate source outside the private device,
do not install the adapter, and do not execute it. Keep live rollback blocked.

Next check: classify the exact tmux session creation form and nested shell
invocation using fixed yes/no labels only, without printing raw script,
arguments, credentials, account names or addresses.
