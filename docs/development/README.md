# Development

This document describes the local development, testing and release workflow for ASF Control Suite.

---

## Repository layout

Production plugin source code lives under:

    src/

The main modules are:

    src/AccountManager/
    src/ControlCenter/
    src/ControlWeb/

Release and build tooling lives under:

    scripts/build/

Developer-only tooling lives under:

    scripts/dev/

Android and phone field-test tooling lives under:

    scripts/phone/

Persistent automated contracts live under:

    tests/

Release pins and SDK verification data live under:

    release/

---

## Canonical release pins

The canonical source for release-critical versions and source revisions is:

    release/pins.env

It defines:

- Control Suite version;
- Control module assembly version;
- ASF version;
- ASF commit;
- ASF-ui commit;
- PlaytimeGoals version;
- PlaytimeGoals commit;
- .NET SDK version.

Do not manually duplicate these values in release scripts or runtime code unless the value is generated from the canonical pin file.

ControlCenter BuildInfo is generated during release preparation from these pins.

---

## Local test suite

Run the complete local test suite with:

    bash tests/run-all.sh

The suite covers:

- repository structure;
- canonical pin parsing;
- single-source pin rules;
- generated BuildInfo;
- RAM-only IPC authentication;
- .NET SDK supply-chain policy;
- native ZIP packaging;
- deterministic archive behavior;
- release provenance;
- JavaScript core logic;
- browser integration;
- transactional phone installation fixtures;
- rollback behavior;
- shell and JavaScript syntax.

A change should not be considered complete while the relevant contract is red.

---

## Exact .NET SDK

Release compilation requires exactly:

    .NET SDK 10.0.400

Verify the selected SDK with:

    bash scripts/build/check-dotnet.sh

If the exact binary is installed outside the normal PATH, select it explicitly:

    export CONTROL_DOTNET="$HOME/.local/share/asf-control-suite/dotnet-10.0.400/dotnet"

Then run the check again:

    bash scripts/build/check-dotnet.sh

The release path fails closed if the exact SDK is unavailable.

---

## Verified SDK bootstrap

For developer machines that do not already have the exact SDK, use:

    bash scripts/dev/bootstrap-dotnet-sdk.sh

The bootstrap:

- uses the SDK version from the canonical release policy;
- supports the approved Linux architectures;
- downloads the official SDK archive;
- verifies the pinned SHA-512 before extraction;
- installs into a user-local directory.

The normal release builder does not silently download or execute a remote SDK installation script.

---

## Exact release build

The canonical release build is:

    bash scripts/build/make-release.sh \
      /path/to/ArchiSteamFarm \
      /path/to/PlaytimeGoals

The supplied repositories must contain the exact pinned commits.

The pipeline:

1. verifies the exact SDK;
2. verifies the canonical release pins;
3. prepares an isolated ASF worktree;
4. checks out the pinned ASF revision;
5. initializes the pinned ASF-ui revision;
6. exports the exact PlaytimeGoals source revision;
7. generates ControlCenter BuildInfo;
8. compiles all plugin projects;
9. treats compiler warnings as errors;
10. creates the canonical plugin stage;
11. generates deterministic native ASF ZIP files;
12. writes release metadata and checksums;
13. verifies complete artifact provenance.

---

## Release output

The canonical build creates:

    artifacts/ASF-Control-Suite-v1.0.0.zip
    artifacts/AccountManager-v1.0.0.zip
    artifacts/ControlCenter-v1.0.0.zip
    artifacts/ControlWeb-v1.0.0.zip
    artifacts/PlaytimeGoals-v0.5.1.zip
    artifacts/CONTROL-SUITE-METADATA.json
    artifacts/SHA256SUMS

Do not manually assemble public ZIP files from arbitrary DLLs.

Bundle and individual archives must come from the same canonical staging tree.

---

## TDD and change discipline

For behavior changes:

1. reproduce the behavior;
2. define the expected behavior with a focused regression contract;
3. confirm RED;
4. implement the smallest correct change;
5. confirm GREEN;
6. run the relevant wider suite;
7. review the diff;
8. commit only after verification.

Bug fixes should address the demonstrated root cause rather than adding retries, hidden fallback behavior or unrelated changes.

---

## Security-sensitive changes

Changes involving authentication, account creation, credentials, packaging, release verification or network exposure require additional care.

Do not introduce:

- arbitrary shell execution;
- arbitrary process creation;
- persistent browser storage for the ASF IPC password;
- plaintext Steam credential persistence;
- a second authentication mechanism;
- ad-hoc release archives outside the canonical packaging scripts;
- release pins maintained independently in multiple places.

ASF-native authentication and APIs remain the primary trust boundary.

---

## Browser integration tests

ControlWeb browser tests exercise desktop and mobile behavior, account flows, localization and lock behavior.

The local environment currently uses Chromium.

Browser test changes should preserve:

- authentication gating;
- RAM-only IPC password handling;
- account-scoped actions;
- ControlWeb localization;
- existing ASF-ui locale integration;
- mobile layout behavior.

Generated screenshots are test artifacts and should not create accidental source drift.

---

## PlaytimeGoals boundary

PlaytimeGoals remains an independent plugin and source repository.

ASF Control Suite pins an exact PlaytimeGoals commit for compatibility and release provenance.

ControlWeb may control PlaytimeGoals through its API, but PlaytimeGoals remains the owner of its internal state and game-goal behavior.

---

## Android field testing

The existing Mi Max 2 deployment path is maintained separately under:

    scripts/phone/

It is used for live field verification and transactional deployment.

The public package format must remain independent from the phone-specific installer.

---

## Files that must not be committed

Do not commit:

- `bin/`;
- `obj/`;
- generated release artifacts;
- runtime ASF configuration;
- Steam credentials;
- IPC passwords;
- cryptkeys;
- runtime databases;
- logs;
- TLS private keys;
- private certificates;
- local backups;
- temporary patch files;
- Python virtual environments.

The repository `.gitignore` contains the baseline exclusions, but contributors are still responsible for reviewing staged changes.

---

## Before committing

Run:

    git diff --check

Then run:

    bash tests/run-all.sh

For changes affecting compilation, dependencies, generated metadata, packaging or release behavior, also perform the exact release build.

Finally inspect:

    git status --short
    git diff --stat
    git diff

Commit only the intended changes.
