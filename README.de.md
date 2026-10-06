<div align="center">

# ASF Control Suite

### Eine sichere, modulare Steuerungsebene für ArchiSteamFarm

**v1.0.0 · ASF 6.3.10.3 · .NET 10.0.400**

[English](README.md) · [Українська](README.uk.md) · [Deutsch](README.de.md)

</div>

---

## Überblick

ASF Control Suite erweitert ArchiSteamFarm um eine einheitliche `/Control/`-Oberfläche. Authentifizierung, Bot-Lebenszyklus und Konfiguration bleiben dabei unter der Kontrolle von ASF selbst.

Das Projekt besteht aus kleinen nativen ASF-Plugins und führt weder einen zweiten Daemon noch eine beliebige Shell-Schnittstelle ein.

| Modul | Aufgabe |
| --- | --- |
| **AccountManager** | Kontoübersicht, Steam-Name/Avatar, Bot-Steuerung und QR-/Passwort-Onboarding |
| **ControlCenter** | Laufzeitstatus, Modulstatus und Kompatibilitätsinformationen |
| **ControlWeb** | Einheitliche selbst gehostete `/Control/`-Weboberfläche |
| **PlaytimeGoals** | Spielzeitziele, Warteschlangen, FREE-Lizenzen und Family-View-Wiederherstellung |

---

## Versionen

Die kanonische Quelle für Release-Versionen und Revisionen ist [`release/pins.env`](release/pins.env).

| Komponente | Version / Revision |
| --- | --- |
| ASF Control Suite | **1.0.0** |
| Control-Module | **1.0.0.0** |
| ArchiSteamFarm | **6.3.10.3** |
| ASF Commit | `27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad` |
| ASF-ui Commit | `2b36125533f41e624b2fdcdec44f37ad60c7daaa` |
| PlaytimeGoals | **0.5.1.0** |
| PlaytimeGoals Commit | `fe7343303cb6d8a253a9622904accd4bf37895c0` |
| .NET SDK | **10.0.400** |

---

## Funktionen

### Kontoverwaltung

- Steam-Personanamen und Avatare
- kontospezifische ASF-Aktionen
- nativer Steam-QR-Login
- Passwort-Onboarding über ASF-native APIs
- keine separate Credential-Datenbank

### PlaytimeGoals

- begrenzte und unbegrenzte Spielzeitziele
- kontospezifische Spielwarteschlangen
- Steam-Family-Unterstützung
- automatische FREE-Lizenz-Verarbeitung
- Family-View-Wiederherstellung
- korrigierte F2P-Readiness-Logik in PlaytimeGoals 0.5.1.0

### ControlWeb

- einheitliche `/Control/`-Seite
- Desktop- und Mobile-Layout
- Sprachintegration mit ASF-ui
- lokal gehostete JavaScript-, CSS- und QR-Ressourcen
- keine beliebige Shell-/Prozess-API

---

## Sicherheitsmodell

ASF IPC bleibt die maßgebliche Authentifizierungsschicht.

Das IPC-Passwort existiert nur im **Seitenspeicher** des aktuell authentifizierten Dokuments. Es wird nicht im Browser Storage gespeichert und geht bei Reload, Lock, Logout, Authentifizierungsfehler oder beim Schließen der Seite verloren.

Steam-Passwörter werden vor dem Speichern der BotConfig über ASF verschlüsselt.

ControlWeb stellt keine API für beliebige Shell-Befehle oder Prozessstarts bereit. QR-Erzeugung und Webressourcen bleiben lokal.

Weitere Informationen: [`SECURITY.md`](SECURITY.md).

---

## Native ASF-Pakete

Der kanonische Release-Build erzeugt:

    ASF-Control-Suite-v1.0.0.zip
    AccountManager-v1.0.0.zip
    ControlCenter-v1.0.0.zip
    ControlWeb-v1.0.0.zip
    PlaytimeGoals-v0.5.1.zip
    CONTROL-SUITE-METADATA.json
    SHA256SUMS

Die ZIP-Dateien enthalten bereits das native ASF-Plugin-Layout.

Installation:

1. ASF stoppen.
2. Das gewünschte ZIP direkt nach `<ASF>/plugins/` entpacken.
3. ASF starten.
4. `/Control/` öffnen und die benötigten Module prüfen.

Das Bundle enthält alle vier Plugins.

---

## Reproduzierbarer Release-Prozess

Der Release-Prozess arbeitet fail-closed:

    release/pins.env
          ↓
    exakte Quellrevisionen
          ↓
    exaktes .NET SDK 10.0.400
          ↓
    Build mit warnings-as-errors
          ↓
    kanonischer Plugin-Staging-Baum
          ↓
    deterministische ZIP-Dateien
          ↓
    Metadaten + SHA256SUMS
          ↓
    Provenance-Prüfung

Der Verifier vergleicht die Bytes des exakten Builds mit dem Bundle und den einzelnen ZIP-Dateien.

Ein erneutes Berechnen von `SHA256SUMS` nach einer Manipulation reicht nicht aus, um die Provenance-Prüfung zu umgehen.

---

## Build

Mit lokalen ASF- und PlaytimeGoals-Git-Repositories, die die gepinnten Revisionen enthalten:

    bash scripts/build/make-release.sh \
      /path/to/ArchiSteamFarm \
      /path/to/PlaytimeGoals

Die vollständige Anleitung befindet sich unter [`docs/installation/manual.md`](docs/installation/manual.md).

---

## Tests

Die vollständige lokale Testsuite:

    bash tests/run-all.sh

Sie prüft unter anderem:

- Integrität der Release-Pins
- generierte BuildInfo
- RAM-only IPC-Authentifizierung
- .NET-SDK-Supply-Chain
- deterministische ZIP-Erzeugung
- Byte-Identität zwischen Build und Paketen
- Release-Provenance
- ControlWeb-Logik
- Browser-Integration
- transaktionale Phone-Deployment- und Rollback-Fixtures

---

## Dokumentation

- [Installation](docs/installation/manual.md)
- [Architektur](docs/architecture/README.md)
- [Entwicklung](docs/development/README.md)
- [Funktionsmatrix](docs/FUNCTION_MATRIX.md)
- [Sicherheitsrichtlinie](SECURITY.md)
- [Mitwirken](CONTRIBUTING.md)

---

<div align="center">

**ASF Control Suite v1.0.0**

ASF-native APIs, reproduzierbare Builds und klar definierte Sicherheitsgrenzen.

</div>
