# Persistent ledger — v1.0

## Completed in sandbox

- [x] Exact ASF 6.3.10.3 and ASF-ui plugin/API research.
- [x] Exact current PlaytimeGoals main pinned at `6d1679a9...`.
- [x] Four-module ownership architecture.
- [x] Account lifecycle workspace and native RequiredInput flow.
- [x] AES-encrypted new-account password persistence.
- [x] Credential-free global defaults with recursive secret filtering.
- [x] Full PlaytimeGoals editor with OWN/FAMILY/FREE/EXCLUDED semantics.
- [x] Single GamesPlayed-owner enforcement.
- [x] Session auto-lock, no-store API fetches, CSP and no external UI dependencies.
- [x] Runtime/storage/module ControlCenter status.
- [x] Native ASF restart/exit only; no web shell.
- [x] Exact four-plugin release builder.
- [x] Transactional phone installer with staging, hashes and automatic rollback.
- [x] Manual rollback and read-only verification scripts.
- [x] Static, unit, Chromium and fake-phone transaction tests.
- [x] 1.0 UI polish: responsive layout, dialogs/toasts, status cards, progress, Family View UI, loading/error/empty states.
- [x] Desktop + 390 px mobile visual QA and accessibility/overflow smoke checks.

## Mandatory PC gate before install

- [ ] Run exact .NET SDK 10.0.400 restore/build against ASF 6.3.10.3.
- [ ] Resolve any compiler/analyzer warnings; plugin build uses warnings-as-errors.
- [ ] Generate the release archive and its hashes.

## Live test after installation

- [ ] Execute `docs/FIELD_TEST.md` against the real Steam/Family/Family View runtime.
