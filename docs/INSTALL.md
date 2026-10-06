# Build and install

## 1. Build one exact release archive

Run from the v1.0 source directory on the Arch Linux machine:

```bash
bash scripts/make-release.sh /path/to/ArchiSteamFarm /path/to/PlaytimeGoals
```

Expected artifact:

```text
artifacts/asf-control-suite-v1.0-dist.tar.gz
```

The release builder requires exact ASF 6.3.10.3 source commit, exact ASF-ui submodule, exact PlaytimeGoals source commit and .NET SDK 10.0.400. It aborts instead of silently building a different combination.

## 2. Read-only phone preflight

```bash
bash scripts/phone-preflight-via-adb.sh
```

## 3. Transactional install

```bash
bash scripts/phone-install-via-adb.sh artifacts/asf-control-suite-v1.0-dist.tar.gz
```

The installer verifies the archive locally and after ADB transfer, stages files, backs up current plugin directories, stops only the ASF child, swaps the four plugin directories, waits for the existing supervisor to bring ASF back, verifies installed hashes and checks root/API/Control/OpenAPI health. A failed post-swap gate triggers automatic rollback.

The installer does **not** replace `/opt/asf/www`, does not kill `asf-proxy` or `tailscale-watch`, and does not delete existing PlaytimeGoals state/database files.

## 4. Verify again at any time

```bash
bash scripts/phone-verify-via-adb.sh
```

## 5. Manual rollback

Latest backup:

```bash
bash scripts/phone-rollback-via-adb.sh
```

Specific backup:

```bash
bash scripts/phone-rollback-via-adb.sh 20261003T120000Z-12345
```

Manual rollback preserves the current `AccountManager.defaults.json` by default. To restore that config file to its pre-install state too:

```bash
CONTROL_ROLLBACK_CONFIG=1 bash scripts/phone-rollback-via-adb.sh
```
