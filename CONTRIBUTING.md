# Contributing

Thanks for contributing to ASF Control Suite.

The project intentionally keeps a small security boundary and a reproducible release process. Changes should preserve both.

---

## Before changing code

For behavior changes or bug fixes:

1. reproduce the current behavior;
2. identify the root cause;
3. add or update a focused regression test;
4. confirm the test fails for the expected reason;
5. implement the smallest correct change;
6. confirm the focused test passes;
7. run the wider test suite;
8. review the final diff before committing.

Avoid speculative fixes, silent fallbacks and unrelated refactors inside a bug fix.

---

## Canonical release data

Release-critical versions and source revisions come from:

    release/pins.env

Do not introduce a second independent source for:

- Control Suite version;
- Control module version;
- ASF version or commit;
- ASF-ui commit;
- PlaytimeGoals version or commit;
- .NET SDK version.

Generated metadata should be derived from the canonical pins.

---

## Security boundaries

Do not introduce:

- arbitrary shell execution;
- arbitrary process creation;
- persistent browser storage for the ASF IPC password;
- plaintext Steam credential persistence;
- a second authentication system;
- unrestricted filesystem APIs;
- remote QR generation that leaks Steam challenge URLs;
- ad-hoc release packages outside the canonical release pipeline.

ASF-native authentication and APIs remain authoritative.

---

## Sensitive data

Never commit:

- Steam passwords;
- login keys;
- Family View PINs;
- ASF IPC passwords;
- ASF cryptkeys;
- bot configuration containing credentials;
- TLS private keys;
- private deployment certificates;
- cookies or API tokens;
- runtime databases;
- account dumps;
- private logs;
- backups containing runtime state.

If sensitive material is accidentally committed, rotate the affected credential and remove the material from Git history before publication.

---

## Tests

Before committing, run:

    git diff --check

Then run:

    bash tests/run-all.sh

Changes affecting compilation, dependencies, generated metadata, packaging or release behavior should also be verified through the exact release pipeline described in:

    docs/development/README.md

---

## Release artifacts

Do not manually assemble public ZIP files from arbitrary DLLs.

The canonical packaging pipeline must remain the source of the versioned artifacts derived from `release/pins.env`:

    ASF-Control-Suite-v<CONTROL_SUITE_VERSION>.zip
    AccountManager-v<CONTROL_SUITE_VERSION>.zip
    ControlCenter-v<CONTROL_SUITE_VERSION>.zip
    ControlWeb-v<CONTROL_SUITE_VERSION>.zip
    PlaytimeGoals-v<PLAYTIMEGOALS_VERSION without trailing .0>.zip
    CONTROL-SUITE-METADATA.json
    SHA256SUMS
    asf-control-suite-v<CONTROL_SUITE_VERSION>-dist.tar.gz

Bundle, individual plugin archives and the phone candidate must continue to originate from the same exact CI build. Stable publication uses `.github/workflows/publish-release.yml` and must reference the exact retained CI artifact plus the SHA-256 of the phone candidate that passed live acceptance.

---

## PlaytimeGoals ownership

PlaytimeGoals remains an independent plugin and repository.

ASF Control Suite pins a specific PlaytimeGoals commit for compatibility and release provenance, but Control Suite should not duplicate ownership of PlaytimeGoals internal state.

---

## Commit scope

Keep commits focused.

Before committing, inspect:

    git status --short
    git diff --stat
    git diff

Generated build output, runtime state, temporary files and local development environments should not be committed.

---

## Security reports

Security-sensitive issues should follow the private reporting guidance in:

    SECURITY.md
