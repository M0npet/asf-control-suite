# ASF Control Suite v1.0 — frozen pre-install specification

Baseline: ASF 6.3.10.3 `27bd1d5d...`, ASF-ui `2b361255...`, PlaytimeGoals `6d1679a9...`, control modules `1.0.0.0`.

## Ownership

- PlaytimeGoals alone owns managed GamesPlayed and managed Family View state.
- AccountManager owns cross-bot summary and credential-free defaults only.
- ControlCenter owns safe runtime/module/storage health only.
- ControlWeb owns presentation/orchestration and calls native ASF/plugin APIs.
- Phone deployment/rollback is out-of-band ADB tooling; it is not a browser capability.

## Account and security rules

Account lifecycle uses native ASF endpoints. New SteamPassword is encrypted through native ASF AES before BotConfig write. Defaults never persist known credentials or secret-like keys. IPCPassword remains ASF's API boundary and is held only in page memory for the current authenticated document. UI assets are local-only with CSP and no-referrer policy. ControlWeb reuses the stock ASF-ui `asf-ui:locale` preference; `uk-UA` has a complete ControlWeb catalog and unsupported locales fall back to English without changing the stock preference.

## PlaytimeGoals editing

BotConfig round-trip remains the single config writer: GET bot config → clone → alter only PTG keys/native idle ownership fields → POST bot config. Finite target is positive hours; blank means unlimited/null. Batch is 1..32. OWN/FAMILY/FREE can be newly selected when `CanSelect`; EXCLUDED cannot, while already-managed excluded/missing goals remain removable.

## Installation transaction

Exact release archive → hash validation → target validation → staging → backup → stop ASF child → four-plugin swap → installed-byte validation → ASF restart by existing supervisor → root/API/Control/OpenAPI health. Any post-swap failure restores the backup. `/opt/asf/www`, proxy and Tailscale sessions are outside the mutation set.
