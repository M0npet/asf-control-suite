# Build and installation

This guide covers the canonical build, verification, installation and rollback process for ASF Control Suite v1.0.0.

---

## Requirements

The exact release configuration is defined in:

    release/pins.env

The current release requires:

- ArchiSteamFarm 6.3.10.3
- ASF-ui at the pinned revision
- PlaytimeGoals 0.5.1.0
- .NET SDK 10.0.400

The build intentionally fails if the selected SDK or source revisions do not match the canonical pins.

---

## Verify the .NET SDK

Check the currently selected SDK:

    bash scripts/build/check-dotnet.sh

If .NET 10.0.400 is installed outside the normal PATH, select the exact binary explicitly:

    export CONTROL_DOTNET="$HOME/.local/share/asf-control-suite/dotnet-10.0.400/dotnet"

Then verify again:

    bash scripts/build/check-dotnet.sh

For a developer-local verified SDK installation, the repository also provides:

    bash scripts/dev/bootstrap-dotnet-sdk.sh

The bootstrap verifies the pinned SHA-512 of the official SDK archive before extraction.

The release builder itself does not silently download or execute a remote SDK installer.

---

## Build the canonical release

You need local Git repositories containing the pinned ASF and PlaytimeGoals commits.

Run:

    bash scripts/build/make-release.sh \
      /path/to/ArchiSteamFarm \
      /path/to/PlaytimeGoals

The release pipeline performs:

1. exact SDK validation;
2. exact ASF revision validation;
3. exact ASF-ui revision validation;
4. exact PlaytimeGoals source export;
5. generated BuildInfo creation;
6. warnings-as-errors compilation;
7. canonical plugin staging;
8. deterministic ZIP generation;
9. metadata and checksum generation;
10. release provenance verification.

---

## Release artifacts

A successful canonical build produces:

    artifacts/ASF-Control-Suite-v1.0.0.zip
    artifacts/AccountManager-v1.0.0.zip
    artifacts/ControlCenter-v1.0.0.zip
    artifacts/ControlWeb-v1.0.0.zip
    artifacts/PlaytimeGoals-v0.5.1.zip
    artifacts/CONTROL-SUITE-METADATA.json
    artifacts/SHA256SUMS

The combined Control Suite ZIP contains the audited patched `ArchiSteamFarm.dll` plus `plugins/...`. Individual plugin ZIPs remain plugin-only.

`CONTROL-SUITE-METADATA.json` and `SHA256SUMS` are release metadata and are not extracted into ASF.

---

## Verify checksums

From the repository root:

    cd artifacts
    sha256sum -c SHA256SUMS
    cd ..

A valid result must report every listed artifact as OK.

Checksum verification is only the first layer. The canonical release pipeline also compares packaged files byte-for-byte against the exact build outputs.

---

## Install the complete suite

Use:

    ASF-Control-Suite-v1.0.0.zip

First stop ASF.

Then extract the ZIP directly into:

    <ASF>/

The bundle contains the patched ASF core at the install root and plugins under the native plugin directory.

After extraction, the important paths are:

    <ASF>/ArchiSteamFarm.dll
    <ASF>/plugins/AccountManager/AccountManager.dll
    <ASF>/plugins/ControlCenter/ControlCenter.dll
    <ASF>/plugins/ControlWeb/ControlWeb.dll
    <ASF>/plugins/ControlWeb/www/
    <ASF>/plugins/PlaytimeGoals/PlaytimeGoals.dll

Do not extract the complete suite ZIP into `<ASF>/plugins/`; it is an install-root bundle.

Start ASF again and open:

    /Control/

Verify that the expected accounts, modules and PlaytimeGoals state are available.

---

## Install individual plugins

The same installation rule applies to the individual archives:

    AccountManager-v1.0.0.zip
    ControlCenter-v1.0.0.zip
    ControlWeb-v1.0.0.zip
    PlaytimeGoals-v0.5.1.zip

For each archive:

1. stop ASF;
2. extract the ZIP directly into `<ASF>/plugins/`;
3. start ASF;
4. verify the plugin.

ControlWeb requires its included `ControlWeb/www/` directory.

---

## What is not included

Public release ZIPs do not contain:

- ASF bot configuration;
- Steam passwords;
- Steam login keys;
- ASF IPC passwords;
- cryptkeys;
- runtime databases;
- logs;
- local backups;
- TLS private keys;
- deployment-specific certificates.

Existing ASF configuration and runtime state remain outside the package.

---

## Updating an existing installation

Before updating, back up the plugin directories being replaced.

Recommended sequence:

1. stop ASF;
2. back up the current plugin directories;
3. extract the complete suite ZIP into `<ASF>/`;
4. start ASF;
5. verify `/Control/`;
6. verify account actions;
7. verify PlaytimeGoals state.

Do not delete existing ASF config or PlaytimeGoals state databases during a normal plugin update.

---

## Rollback

If an update fails:

1. stop ASF;
2. restore the previous `ArchiSteamFarm.dll` and plugin directories from backup;
4. start ASF;
5. verify `/Control/` and PlaytimeGoals state.

Because runtime configuration and databases are outside the native release ZIPs, replacing plugin binaries does not require replacing those files.

---

## Advanced Android deployment

The repository also contains Android/ADB deployment tooling under:

    scripts/phone/

That path is intended for the existing Mi Max 2 field-test environment and supports transactional deployment, backup, verification and rollback.

It is separate from the public native ZIP installation model.

The normal public installation path remains:

    stop ASF
      ↓
    extract complete suite ZIP into <ASF>/
      ↓
    start ASF
      ↓
    verify /Control/
