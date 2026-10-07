# Native ASF UI parity — Phase 1 spec

## Goal

Make Control Suite the primary place for standard ASF administration instead of routing normal work through stock ASF-ui.

Phase 1 moves the highest-value native surfaces into ControlWeb:

1. Full per-bot BotConfig editor.
2. Full global ASF config editor.
3. Native command terminal.
4. IPC ban management.

Stock ASF-ui remains available only as an emergency compatibility fallback.

## Design principles

- ASF remains the source of truth. ControlWeb uses the pinned native ASF API and never writes config files directly.
- The editor is schema-agnostic at runtime: it renders the complete config object returned by ASF, so newly-added ASF fields are visible without manually teaching ControlWeb each property.
- Primitive fields receive native controls; arrays and objects use validated JSON editors.
- Security-controlled fields are never rendered with their stored values. They are omitted on save so ASF preserves the existing values through its native inheritance logic.
- Every mutation is scoped and confirmed where destructive or process-wide.
- IPC password remains page-memory-only.
- No arbitrary host or shell execution is added.

## Protected fields

BotConfig values omitted from the generic editor:

- SteamLogin
- SteamPassword
- SteamParentalCode
- WebProxyPassword

GlobalConfig values omitted:

- IPCPassword
- LicenseID
- WebProxyPassword

ASF's native POST handlers preserve existing protected values when those properties are omitted.

## UX

A new **ASF Native** navigation view contains tabs:

- Bot config
- Global config
- Commands
- Bans

The bot editor follows the selected account from Control Suite's existing account switcher.

The generic config editor supports:

- boolean -> checkbox
- finite number -> number input
- string -> text input
- array/object -> JSON textarea with validation
- null/unknown -> JSON textarea

Fields are searchable and sorted alphabetically.

## Save semantics

### BotConfig

GET `/Api/Bot/{bot}` -> edit complete `BotConfig` -> POST `/Api/Bot/{bot}` with `{ BotConfig }`.

Protected values are removed before POST. ASF preserves the existing values.

### GlobalConfig

GET `/Api/ASF` -> edit `GlobalConfig` -> POST `/Api/ASF` with `{ GlobalConfig }`.

Protected values are removed before POST. ASF preserves them. The UI warns that global changes can restart/reload ASF.

### Commands

POST `/Api/Command` with `{ Command }`. History is tab-local only.

### Bans

GET/DELETE through `/Api/IPC/Bans`.

## Acceptance

- No legacy ASF-ui page is required to edit a normal bot config.
- All non-protected BotConfig fields returned by ASF are editable.
- All non-protected GlobalConfig fields returned by ASF are editable.
- Invalid JSON in complex fields blocks save.
- Commands execute and responses remain on-page.
- Bans can refresh, remove one, or remove all.
- RAM-only IPC credential rules remain unchanged.
- Existing account, QR, PlaytimeGoals, Security, System and installer tests remain green.
