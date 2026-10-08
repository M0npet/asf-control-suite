<div align="center">

# ASF Control Suite

### Eine sichere, modulare Steuerungsebene für ArchiSteamFarm

**main: v1.1.0 candidate · stable: v1.0.0 · ASF 6.3.10.3 · .NET 10.0.400**

[English](README.md) · [Українська](README.uk.md) · [Deutsch](README.de.md)

</div>

---

## Überblick

ASF Control Suite erweitert ArchiSteamFarm um eine einheitliche Oberfläche mit `/` als Standard-Einstieg und `/Control/` als kanonischem internem Pfad. Authentifizierung, Bot-Lebenszyklus und Konfiguration bleiben dabei unter der Kontrolle von ASF selbst.

Das Projekt besteht aus kleinen nativen ASF-Plugins und führt weder einen zweiten Daemon noch eine beliebige Shell-Schnittstelle ein.

| Modul | Aufgabe |
| --- | --- |
| **AccountManager** | Kontoübersicht, Steam-Name/Avatar, Bot-Steuerung und QR-/Passwort-Onboarding |
| **ControlCenter** | Laufzeitstatus, Modulstatus und Kompatibilitätsinformationen |
| **ControlWeb** | Selbst gehostete Weboberfläche; `/` ist der Standard-Einstieg, `/Control/` der kanonische interne Pfad |
| **PlaytimeGoals** | Spielzeitziele, Warteschlangen, FREE-Lizenzen und Family-View-Wiederherstellung |

---

## Versionen

Die kanonische Quelle für Release-Versionen und Revisionen ist [`release/pins.env`](release/pins.env).

| Komponente | Version / Revision |
| --- | --- |
| ASF Control Suite | **1.1.0 candidate** |
| Control-Module | **1.1.0.0** |
| ArchiSteamFarm | **6.3.10.3** |
| ASF Commit | `27bd1d5dbdc8c4897eaaed0e3246d10ffe18b0ad` |
| ASF-ui Commit | `2b36125533f41e624b2fdcdec44f37ad60c7daaa` |
| PlaytimeGoals | **0.5.3.0** |
| PlaytimeGoals Commit | `f7c1bfe74c9203fe089830f1646a3d2ba54150de` |
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
- sekundengenaue lokale Deadlines für begrenzte Ziele in PlaytimeGoals 0.5.3

### ControlWeb

- `/` öffnet Control Suite standardmäßig; `/Control/` bleibt der kanonische interne Pfad
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

    ASF-Control-Suite-v1.1.0.zip
    AccountManager-v1.1.0.zip
    ControlCenter-v1.1.0.zip
    ControlWeb-v1.1.0.zip
    PlaytimeGoals-v0.5.2.zip
    CONTROL-SUITE-METADATA.json
    SHA256SUMS

Die ZIP-Dateien enthalten bereits das native ASF-Plugin-Layout.

Installation des vollständigen Bundles:

1. ASF stoppen.
2. `ASF-Control-Suite-v1.1.0.zip` direkt in `<ASF>/` entpacken.
3. ASF starten.
4. `/` öffnen und Control Suite sowie `/Control/` prüfen.

Einzelne Plugin-ZIPs werden direkt nach `<ASF>/plugins/` entpackt.

Die oben genannten Paketnamen gehören zum aktuellen v1.1.0-Kandidaten auf `main`. Stabil bleibt [v1.0.0](https://github.com/M0npet/asf-control-suite/releases/tag/v1.0.0), bis der neue Kandidat die Live-Abnahme bestanden hat.

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

**ASF Control Suite · main v1.1.0 candidate · stable v1.0.0**

ASF-native APIs, reproduzierbare Builds und klar definierte Sicherheitsgrenzen.

</div>
