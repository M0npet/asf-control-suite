<div align="center">

# ASF Control Suite

### Native account control, web UI and playtime automation for ArchiSteamFarm

<p>
  <a href="https://github.com/M0npet/asf-control-suite/releases/tag/v1.0.0">
    <img alt="Release" src="https://img.shields.io/github/v/release/M0npet/asf-control-suite?display_name=tag&sort=semver">
  </a>
  <img alt="ASF 6.3.10.3" src="https://img.shields.io/badge/ASF-6.3.10.3-2f81f7">
  <img alt=".NET 10.0.400" src="https://img.shields.io/badge/.NET_SDK-10.0.400-512BD4?logo=dotnet&logoColor=white">
  <a href="https://github.com/M0npet/asf-control-suite/releases">
    <img alt="Downloads" src="https://img.shields.io/github/downloads/M0npet/asf-control-suite/total">
  </a>
  <a href="LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/M0npet/asf-control-suite">
  </a>
</p>

**One self-hosted `/Control/` UI · ASF-native APIs · reproducible releases · RAM-only IPC credentials**

[**Download v1.0.0**](https://github.com/M0npet/asf-control-suite/releases/tag/v1.0.0)
&nbsp;·&nbsp;
[Installation](docs/installation/manual.md)
&nbsp;·&nbsp;
[Security](SECURITY.md)
&nbsp;·&nbsp;
[Release notes](docs/RELEASE_NOTES.md)

[English](README.md) · [Українська](README.uk.md) · [Deutsch](README.de.md)

</div>

<p align="center">
  <img src="docs/screenshots/dashboard-desktop.png" alt="ASF Control Suite dashboard" width="920">
</p>

---

## Overview

ASF Control Suite adds a unified control layer to
[ArchiSteamFarm](https://github.com/JustArchiNET/ArchiSteamFarm)
while keeping ASF itself authoritative for authentication, bot lifecycle and configuration.

No second daemon. No arbitrary shell API. No separate credential database.

| Module | Purpose |
| --- | --- |
| **AccountManager** | Multi-account overview, Steam profiles, bot controls and QR/password onboarding |
| **ControlCenter** | Runtime health, module status and compatibility metadata |
| **ControlWeb** | Responsive self-hosted `/Control/` interface |
| **PlaytimeGoals** | Per-game playtime targets, queues, FREE-license handling and Family View recovery |

## Preview

<table>
  <tr>
    <td width="62%">
      <img src="docs/screenshots/playtime-desktop.png" alt="PlaytimeGoals desktop">
    </td>
    <td width="38%">
      <img src="docs/screenshots/playtime-mobile.png" alt="PlaytimeGoals mobile">
    </td>
  </tr>
  <tr>
    <td align="center"><strong>Desktop</strong></td>
    <td align="center"><strong>Mobile</strong></td>
  </tr>
</table>

<details>
<summary><strong>Ukrainian interface</strong></summary>
<br>

<table>
  <tr>
    <td width="62%">
      <img src="docs/screenshots/dashboard-uk-desktop.png" alt="Ukrainian dashboard">
    </td>
    <td width="38%">
      <img src="docs/screenshots/playtime-uk-mobile.png" alt="Ukrainian mobile interface">
    </td>
  </tr>
</table>

</details>

## Quick install

1. Download **ASF-Control-Suite-v1.0.0.zip** from the
   [v1.0.0 release](https://github.com/M0npet/asf-control-suite/releases/tag/v1.0.0).
2. Stop ASF.
3. Extract the archive directly into `<ASF>/plugins/`.
4. Start ASF.
5. Open `/Control/`.
6. Authenticate with your normal ASF IPC password.

For individual packages, upgrades and manual builds, see the
[installation guide](docs/installation/manual.md).

## Highlights

- **ASF-native authentication** — ASF IPC remains authoritative.
- **RAM-only IPC password** — credentials are never persisted to browser storage.
- **Responsive UI** — desktop and mobile layouts.
- **Self-hosted assets** — CSS, JavaScript and QR rendering stay local.
- **Pinned supply chain** — ASF, ASF-ui, PlaytimeGoals and .NET SDK revisions are explicit.
- **Verified release provenance** — archives are checked against canonical build output.
- **Transactional deployment** — validation, backup, verification and rollback support.

## Compatibility

The canonical source of truth is [`release/pins.env`](release/pins.env).

| Component | Version |
| --- | --- |
| ASF Control Suite | **1.0.0** |
| Control modules | **1.0.0.0** |
| ArchiSteamFarm | **6.3.10.3** |
| PlaytimeGoals | **0.5.1.0** |
| .NET SDK | **10.0.400** |

Pinned revisions:

- ASF: `27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad`
- ASF-ui: `2b36125533f41e624b2fdcdec44f37ad60c7daaa`
- PlaytimeGoals: `fe7343303cb6d8a253a9622904accd4bf37895c0`

## Release integrity

The verified `v1.0.0` release is anchored to commit `e5a8227`.

Public Control Suite release assets:

    ASF-Control-Suite-v1.0.0.zip
    AccountManager-v1.0.0.zip
    ControlCenter-v1.0.0.zip
    ControlWeb-v1.0.0.zip
    CONTROL-SUITE-METADATA.json
    SHA256SUMS

Verify downloads with:

    sha256sum -c SHA256SUMS

PlaytimeGoals is built and provenance-verified with the suite, but its
standalone ZIP belongs to the separate PlaytimeGoals public release.

## Security

The IPC password exists only in JavaScript **page memory** for the
authenticated page.

It is cleared on refresh, lock, logout, authentication rejection or page
close and is not stored in `localStorage` or `sessionStorage`.

Steam passwords are encrypted through ASF before BotConfig persistence.

ControlWeb exposes no arbitrary shell/process execution API.

See [SECURITY.md](SECURITY.md).

## Testing

Run the complete local suite:

    bash tests/run-all.sh

The suite covers:

- release pin integrity
- generated build metadata
- RAM-only authentication
- .NET SDK supply-chain validation
- native ZIP layout
- byte identity
- release provenance
- browser integration
- transactional phone installation and rollback

## Repository layout

    src/          ASF plugin source
    release/      canonical release pins
    scripts/      build, packaging and deployment tools
    installer/    transactional phone deployment
    tests/        contract and integration tests
    docs/         user and developer documentation

## Documentation

- [Installation](docs/installation/manual.md)
- [Architecture](docs/architecture/README.md)
- [Development](docs/development/README.md)
- [Function matrix](docs/FUNCTION_MATRIX.md)
- [Release notes](docs/RELEASE_NOTES.md)
- [Test report](docs/TEST_REPORT.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [License](LICENSE)

---

<div align="center">

**ASF Control Suite**

ASF-native APIs · explicit security boundaries · reproducible releases

</div>
