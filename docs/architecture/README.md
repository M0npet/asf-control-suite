# Architecture

ASF Control Suite extends ArchiSteamFarm through ASF-native plugin and web interfaces.

It does not replace ASF with a second daemon and does not introduce an arbitrary shell or process-execution API.

---

## Components

The suite consists of four cooperating modules.

### AccountManager

AccountManager owns account-oriented operations.

Its responsibilities include:

- cross-bot account summaries;
- Steam persona names and avatars;
- ASF-native bot lifecycle actions;
- QR-based Steam onboarding;
- password-based onboarding;
- credential-free account defaults.

Steam passwords are encrypted through ASF before BotConfig persistence.

AccountManager does not maintain a second plaintext credential database.

---

### ControlCenter

ControlCenter provides read-only runtime and compatibility information for the suite.

It exposes:

- Control Suite version;
- individual module versions;
- target ASF version and commit;
- target ASF-ui commit;
- target PlaytimeGoals version and commit;
- target .NET SDK version;
- safe runtime/module health information.

Release metadata is generated from the canonical values in:

    release/pins.env

Runtime members that are unsafe or unreliable on the trimmed ASF target are deliberately avoided.

---

### ControlWeb

ControlWeb provides the unified web interface at:

    /Control/

It serves its own:

- HTML;
- JavaScript;
- CSS;
- localization catalog;
- QR renderer.

The web layer communicates with ASF and plugin APIs rather than invoking host commands.

There is no arbitrary shell or process-execution endpoint.

---

### PlaytimeGoals

PlaytimeGoals remains a separate ASF plugin and owns its own state machine.

It controls:

- game-goal queues;
- managed GamesPlayed state;
- finite and unlimited playtime targets;
- FREE-license claim behavior;
- Steam Family handling;
- managed Family View recovery.

ControlWeb provides an interface to PlaytimeGoals but does not duplicate ownership of this state.

---

## Authentication boundary

ASF IPC authentication remains authoritative.

The browser sends the normal ASF authentication header when calling protected APIs.

The IPC password exists only in JavaScript page memory for the current authenticated document.

It is not restored after page refresh and is cleared on:

- manual lock;
- automatic inactivity lock;
- logout;
- authentication rejection;
- document close.

Legacy browser-persisted IPC credentials are removed by one-way migration cleanup.

Non-secret UI preferences may still use browser storage where appropriate.

---

## Web security boundary

ControlWeb uses self-hosted assets and a restrictive Content Security Policy.

QR challenges are rendered locally rather than being sent to a third-party QR service.

The application does not expose:

- arbitrary shell execution;
- arbitrary process creation;
- unrestricted filesystem operations;
- a second authentication system;
- a persistent IPC credential store.

Destructive or state-changing operations remain scoped to ASF/plugin APIs.

---

## Canonical release inputs

The canonical release definition lives in:

    release/pins.env

It pins:

- Control Suite version;
- Control module version;
- ASF version;
- ASF commit;
- ASF-ui commit;
- PlaytimeGoals version;
- PlaytimeGoals commit;
- .NET SDK version.

Release-critical version information must not be maintained independently in multiple places.

Generated BuildInfo is derived from these canonical pins.

---

## Exact build path

The release process prepares an isolated build tree using the exact pinned source revisions.

The sequence is:

    release/pins.env
          ↓
    exact ASF revision
          ↓
    exact ASF-ui revision
          ↓
    exact PlaytimeGoals source
          ↓
    generated BuildInfo
          ↓
    exact .NET SDK 10.0.400
          ↓
    warnings-as-errors compilation

All four plugin DLLs are built from this controlled source set.

---

## Packaging architecture

Release packaging uses one canonical plugin staging tree.

That tree contains only installable plugin payloads:

    AccountManager/
    ControlCenter/
    ControlWeb/
    PlaytimeGoals/

ControlWeb additionally contains:

    ControlWeb/www/

The same canonical stage is used to create:

- the complete suite ZIP;
- every individual plugin ZIP.

This prevents the bundle and standalone packages from drifting apart.

---

## Deterministic archives

Native ASF ZIP files are generated deterministically.

For identical input files, the packager fixes:

- member ordering;
- ZIP timestamps;
- file modes;
- compression behavior.

This allows repeated builds from identical inputs to produce identical ZIP bytes.

---

## Provenance verification

Release verification checks the complete chain:

    canonical pins
          ↓
    release metadata
          ↓
    SHA256SUMS
          ↓
    exact build output
          ↓
    bundle ZIP
          ↓
    individual ZIP files

The verifier checks exact ZIP member sets and compares every packaged payload byte-for-byte against the build output.

Changing an artifact and then regenerating `SHA256SUMS` is not sufficient to pass provenance verification.

---

## Installation boundary

Native release ZIP files represent the contents of:

    <ASF>/plugins/

They do not contain deployment-specific runtime state.

Excluded data includes:

- ASF bot configuration;
- Steam credentials;
- IPC passwords;
- cryptkeys;
- runtime databases;
- logs;
- local backups;
- TLS private material.

Configuration and runtime state remain owned by the ASF installation.

---

## Android deployment boundary

The repository also contains Android/ADB transaction tooling for the existing Mi Max 2 field-test environment.

That tooling provides staging, backup, byte verification, health checks and rollback.

It is an operational deployment layer and is deliberately separate from the public native ASF ZIP format.
