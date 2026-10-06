<div align="center">

# ASF Control Suite

### A safe, modular control layer for ArchiSteamFarm

**v1.0.0 · ASF 6.3.10.3 · .NET 10.0.400**

[English](README.md) · [Українська](README.uk.md) · [Deutsch](README.de.md)

</div>

---

## Overview

ASF Control Suite adds a unified `/Control/` interface to ArchiSteamFarm while keeping ASF itself in control of authentication, bot lifecycle and configuration.

The project is split into small ASF-native modules instead of introducing a second daemon or an arbitrary shell interface.

| Module | Purpose |
| --- | --- |
| **AccountManager** | Multi-account overview, Steam persona/avatar data, bot controls and QR/password onboarding |
| **ControlCenter** | Runtime health, module status and compatibility metadata |
| **ControlWeb** | Unified self-hosted `/Control/` web interface |
| **PlaytimeGoals** | Per-game playtime goals, queue management, FREE-license handling and Family View recovery |

---

## Version matrix

The canonical release source of truth is [`release/pins.env`](release/pins.env).

| Component | Version / revision |
| --- | --- |
| ASF Control Suite | **1.0.0** |
| Control modules | **1.0.0.0** |
| ArchiSteamFarm | **6.3.10.3** |
| ASF commit | `27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad` |
| ASF-ui commit | `2b36125533f41e624b2fdcdec44f37ad60c7daaa` |
| PlaytimeGoals | **0.5.1.0** |
| PlaytimeGoals commit | `fe7343303cb6d8a253a9622904accd4bf37895c0` |
| .NET SDK | **10.0.400** |

---

## Highlights

### Account management

- Steam persona names and avatars
- account-scoped ASF actions
- native Steam QR login flow
- password onboarding through ASF-native APIs
- no separate credential database

### PlaytimeGoals

- finite and unlimited playtime targets
- account-scoped game queues
- Steam Family awareness
- FREE-license auto-claim handling
- Family View recovery
- fixed F2P readiness behavior in PlaytimeGoals 0.5.1.0

### Control interface

- unified `/Control/` page
- desktop and mobile layouts
- English, Ukrainian and ASF-ui locale integration
- self-hosted JavaScript, CSS and QR rendering
- no arbitrary shell/process execution surface

---

## Security model

ASF IPC authentication remains authoritative.

The IPC password exists only in JavaScript **page memory** for the currently authenticated document. It is not persisted in browser storage and is discarded on refresh, lock, logout, authentication rejection or page close.

Steam passwords are encrypted through ASF before BotConfig persistence.

ControlWeb does not expose an arbitrary shell or process execution API. QR rendering and web assets are local and self-hosted.

See [`SECURITY.md`](SECURITY.md) for the project security policy.

---

## Native ASF packages

The canonical release build produces:

    ASF-Control-Suite-v1.0.0.zip
    AccountManager-v1.0.0.zip
    ControlCenter-v1.0.0.zip
    ControlWeb-v1.0.0.zip
    PlaytimeGoals-v0.5.1.zip
    CONTROL-SUITE-METADATA.json
    SHA256SUMS

The bundle and individual ZIP files use the native ASF plugin layout.

To install a package:

1. Stop ASF.
2. Extract the selected ZIP directly into `<ASF>/plugins/`.
3. Start ASF.
4. Open `/Control/` and verify the required modules.

The bundle ZIP contains all four plugins.

---

## Reproducible release pipeline

The release path is deliberately fail-closed:

    release/pins.env
          ↓
    exact source revisions
          ↓
    exact .NET SDK 10.0.400
          ↓
    warnings-as-errors build
          ↓
    canonical plugin staging tree
          ↓
    deterministic native ZIP files
          ↓
    metadata + SHA256SUMS
          ↓
    release provenance verification

The verifier compares the exact build output with both the bundle and individual archives.

Recalculating `SHA256SUMS` after modifying an artifact is not enough to bypass the provenance gate.

---

## Build

With local ASF and PlaytimeGoals Git repositories containing the pinned revisions:

    bash scripts/build/make-release.sh \
      /path/to/ArchiSteamFarm \
      /path/to/PlaytimeGoals

The release build requires the exact SDK selected by the repository policy.

Full instructions are available in [`docs/installation/manual.md`](docs/installation/manual.md).

---

## Testing

Run the complete local test suite:

    bash tests/run-all.sh

The suite covers, among other things:

- release pin integrity
- generated build metadata
- RAM-only IPC authentication
- .NET SDK supply-chain verification
- deterministic ZIP packaging
- build/package byte identity
- release provenance
- ControlWeb logic
- browser integration
- transactional phone deployment and rollback fixtures

---

## Documentation

- [Installation](docs/installation/manual.md)
- [Architecture](docs/architecture/README.md)
- [Development](docs/development/README.md)
- [Function matrix](docs/FUNCTION_MATRIX.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

---

<div align="center">

**ASF Control Suite v1.0.0**

Built around ASF-native APIs, reproducible builds and explicit security boundaries.

</div>
