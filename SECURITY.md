# Security Policy

## Sensitive data

Never commit or publish:

- ASF bot configuration containing credentials
- Steam login credentials or login keys
- Steam Family View PINs
- ASF IPC passwords
- cryptkey files
- TLS private keys or certificates used by a private deployment
- cookies, session tokens or API tokens
- runtime databases
- private account dumps
- runtime logs containing account information
- local backup files

If sensitive data is committed, rotate the affected credential and remove
the data from Git history before publishing.

## Reporting

Please report security issues privately to the repository owner instead of
opening a public issue containing exploit details or secrets.

## Trust boundary

ASF Control Suite uses ASF's native IPC authentication. The project must not
introduce an arbitrary shell/process execution API or its own persistent
credential store.


## Native ASF workspace

The v1.1 Native ASF workspace is intentionally powerful, but it stays inside ASF's authenticated IPC boundary.

- BotConfig security-controlled values are omitted from the raw editor and preserved on normal saves.
- `SteamTradeToken` is explicitly omitted from the editor and from copied bot configs.
- GlobalConfig omits `IPCPassword`, `LicenseID` and `WebProxyPassword`; ASF's native GlobalConfig write path preserves omitted values.
- The generic command console blocks ASF self-update, plugin self-update, restart and exit commands. Restart/exit remain available only through dedicated typed-confirmation controls.
- Background Redeemer is write-only in Control Suite: existing queued/redeemed Steam key material is not fetched into the browser.
- Log history is read through ASF's authenticated `/Api/NLog/File` endpoint; Control Suite adds no arbitrary file-reading API.
- Control Suite does not expose ASF decrypt/file-resolution functionality.
- Native ASF/plugin self-update remains disabled for pinned phone deployments.

## Release trust boundary

A green build is not sufficient to publish a stable release.

The exact CI artifact must pass live acceptance unchanged. Stable publication uses `.github/workflows/publish-release.yml`, which binds the release to an exact source commit and retained CI artifact, verifies `CONTROL-SUITE-COMMIT.txt`, `SHA256SUMS` and the accepted phone-candidate SHA-256, rejects expired/mismatched artifacts, and refuses to reuse an existing tag or release.

If source, dependency pins, packaging or candidate bytes change after live acceptance, the candidate must repeat live acceptance before publication.
