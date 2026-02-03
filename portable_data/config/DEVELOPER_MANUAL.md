# Entwicklerdoku – Modultool Video-Werkstatt (Portable)

Stand: 2026-02-20T10:00:00Z

## Ziel (kurz)
Dieses Tool baut Videos aus Bild+Audio (Standbild-Modus) und kann automatisiert um eine Uhrzeit (globaler Zeitplan) den Downloads-Ordner abarbeiten.
Kernprinzip: **Zwischenablage → Temp → Validierung → Commit** (datensicher).

## Start (Portable)
1. `tools/start.sh`
   - erstellt venv in `portable_data/.venv`
   - installiert PySide6
   - startet `app/main.py`

2. Einmalige Systemeinrichtung (tagsüber):
   - im Tool: **Systemeinrichtung (FFmpeg)**
   - oder: `tools/setup_system.sh`
   - nutzt sudo für `apt install ffmpeg`

3. Automatik (global):
   - Uhrzeit in `portable_data/config/automation_rules.json` → `start_time`
   - Timer einrichten: `tools/install_timer.sh`
   - Automatik-Runner: `tools/run_automation.sh`

## Start-Routine (autonom, mit Nutzerfeedback)
Die Start-Routine ist der **Standardweg**. Sie richtet alles ein und meldet klar, was passiert ist.

- Einstieg: `tools/start.sh`
- Prüft/Installiert Abhängigkeiten (Dependencies = Zusatzpakete)
- Führt den Werkstatt-Check (Preflight = Startprüfung) aus
- Schreibt Logs (Protokolle) nach `portable_data/logs/`
- Debug-Modus: `MODULTOOL_DEBUG=1 tools/start.sh`

## Release-Checks (vollautomatisch)
Ein kompletter, reproduzierbarer Prüfablauf (mit klaren Meldungen):
```bash
tools/run_release_checks.sh
```
Enthält: Python-Compile, Bash-Check, Qualitäts-Checks (ruff), Must-Pass Suite und Release-Builds (ZIP/.deb).

## Ordnerstruktur (Portable)
- Tool (unverändert):
  - `app/` Code
  - `assets/` mitgelieferte Dateien
- Nutzer (veränderlich):
  - `portable_data/user_data/`
    - `exports/YYYY-MM-DD/` Ausgaben
    - `library/audio/YYYY-MM-DD/` genutzte Audios
    - `library/images/YYYY-MM-DD/` genutzte Bilder
    - `staging/YYYY-MM-DD/` Zwischenablage (Input-Dateien, solange nicht validiert)
    - `quarantine/YYYY-MM-DD/` Quarantäne-Ausgaben
    - `quarantine_jobs/quarantine_jobs_YYYY-MM-DD.json` Quarantäne-Aufträge (pro Tag)
    - `reports/run_*.json` Arbeitsberichte
    - `trash/` Papierkorb (erst nach validiertem Commit)
- Konfiguration:
  - `portable_data/config/`
    - `settings.json` globale Einstellungen (Pfade, Audio, Performance, Namensvorlagen)
    - `automation_rules.json` Zeitplan und Scan-Regeln
    - `texte_de.json` Werkstatt-Texte (JSON, versioniert)
    - `themes.json` Sichtmodi (sehschwach)
    - `manifest.json` Features & Versionen
    - `DEVELOPMENT_STATUS.md` Fortschritt + nächster Schritt
    - `DEVELOPER_MANUAL.md` Entwicklerdoku (im Tool sichtbar)
    - `HELP_CENTER.md` Hilfe-Center-Inhalte
    - `CHANGELOG.md` Änderungsverlauf
    - `PROJECT_STRUCTURE.md` Projektverzeichnis (finaler Überblick)
    - `README.txt` Nutzer-Anleitung

## Projektverzeichnis (finaler Überblick)
Die vollständige Liste der Ordner/Dateien samt Zweck steht in:
`portable_data/config/PROJECT_STRUCTURE.md`.

## Architektur (Schichten)
1. **Core-Logik (CLI Runner)**
   - `app/automation_runner.py`
   - macht Scan → Zwischenablage → Render → Validierung → Commit
2. **GUI**
   - `app/main.py`
   - zeigt Schaltzentrale, Auswahlkorb, Letzte-Nacht-Karte, Quarantäne-Aktionen, Entwicklerdoku
3. **Quarantäne-Worker**
   - `app/quarantine_worker.py`
   - bearbeitet Quarantäne-Aufträge erneut (Ton Safe), setzt Status, hakt Tagesliste ab

## Datensicherheit (Commit-Regeln)
- Niemals direkt in Downloads rendern.
- Inputs werden zuerst nach staging verschoben und bekommen `_in_work_TIMESTAMP`.
- Ausgabe wird zuerst in `cache/temp_renders/` erstellt.
- Erst wenn Validierung grün ist:
  - Ausgabe → `exports/...`
  - Inputs → `library/...` mit `_used_TIMESTAMP`
  - staging wird bereinigt
- Bei Fehler:
  - Ausgabe → `quarantine/...` mit `_quarantaene` Suffix
  - Quarantäne-Auftrag wird in Tagesliste geschrieben

## Input/Output-Validierung (Pflicht)
- Jede Funktion prüft Eingaben (Input = Nutzereingabe).
- Jede Funktion bestätigt Ergebnisse (Output = Erfolg/Status).
- Fehler liefern immer den **nächsten Schritt** (z. B. „Jetzt reparieren“, „Sicherer Standard“, „Details“).

## Qualitäts-Validierung (Ton)
- Standard: AAC, 48kHz, 320k (Minimum 192k).
- Nach Export prüft ffprobe:
  - Audio-Samplerate = Ziel
  - Bitrate >= Minimum
  - Wenn fail → kein Commit, Quarantäne.

## Action-IDs (Buttons in Fehlerdialogen / Quarantäne)
- `setup_install_ffmpeg_sudo` → `tools/setup_system.sh`
- `open_last_report` → öffnet letzten `reports/run_*.json`
- `open_quarantine_jobs_today` → öffnet Tagesliste
- `rerun_tone_safe` → Quarantäne-Worker (erneut erstellen)

## Codequalität-Standards (Release-Gates)
- Kein Überschreiben von Dateien: immer `_001` bei Kollision.
- Atomische Moves: temp → final.
- Lockfile gegen Doppelstart: `staging/automation.lock`.
- Logs rotieren (später): Maxgröße, dann Archiv.
- Fehler nie „still“: immer Report + Dashboard-Karte.

## Automatisierte Tests & Qualität
Pflicht für Releases (vollautomatisch):
```bash
tools/run_release_checks.sh
```
Enthält:
- Python-Compile (Syntax-Check)
- Bash-Check (Shell-Skripte)
- Qualitäts-Checks (ruff check + format)
- Must-Pass Suite (Funktionsprüfung)
- Release-Builds (ZIP + .deb)

Zusätzlich (bei Bedarf):
- `tools/run_quality_checks.sh` (Codequalität + Format)
- `tools/run_selftest.sh` (Funktionsprüfung mit Testdaten)

## Barrierefreiheit (Minimum)
- 3 Themes (sehschwach) in `themes.json`.
- Sichtbarer Fokusrahmen, Tastaturbedienung.
- Buttontexte: kurz und eindeutig (deutsch).
- Tooltips erklären Details.

## Debugging & Logging (Pflicht)
- Debug-Modus: `MODULTOOL_DEBUG=1 tools/start.sh` (Debug = Fehlersuche).
- Logs trennen: Nutzer-Feedback (UI) vs. Entwickler-Log (`portable_data/logs/debug.log`).
- Kein Silent-Fail: jede Abweichung wird protokolliert und erklärt.

## Versionierung (Regel im Tool)
Semantische Versionierung (SemVer) ist Pflicht:
- **MAJOR**: breaking change (nicht abwärtskompatibel)
- **MINOR**: neue Funktion (abwärtskompatibel)
- **PATCH**: Bugfix oder Doku-Update

Bei **jedem Release**:
1) `portable_data/config/manifest.json`: `version` erhöhen, `build_date` aktualisieren.
2) `portable_data/config/CHANGELOG.md`: neuer Abschnitt (ein Absatz).
3) `portable_data/config/DEVELOPMENT_STATUS.md`: Fortschritt + nächster Schritt.
4) Git-Tag setzen: `vMAJOR.MINOR.PATCH` (z. B. `v1.0.45`).

## Nächste Schritte (nach 0.9.0)
- Voller Selftest (GUI startet CLI Runner mit Demo-Watchfolder).
- Vollständige UI-Integration für Quarantäne-Tagesliste (als Tabelle mit Edit).
- Plugin-Schnittstelle (Presets/Job-Builder).


## Selftest (0.9.2)
- `tools/run_selftest.sh` erzeugt 1 Erfolg + 1 Quarantäne.
- Reports landen in `user_data/reports/` als `run_selftest_*`.
- GUI aktualisiert danach automatisch 'Letzte Nacht'.

Hinweis: Selftest-Reports werden in user_data/reports/ als run_selftest_* abgelegt, ohne die echte Tages-Quarantäne zu überschreiben.

## Echt-Import (0.9.3)
- Material-Tab unterstützt Drag&Drop und Dateiauswahl/Ordnerwahl.
- Auswahlkorb zeigt echte Dateien und erlaubt Umbenennen/Entfernen aus Auswahl.

## Thumbnails & Bildvorschau (0.9.4)
- Materialliste zeigt Mini-Thumbnails für Bilder (Cache: portable_data/cache/thumbs).
- Klick auf Bild zeigt große Vorschau + Dateiinformation.
- Auswahlkorb zeigt Mini-Thumbs für Bilddateien.

## Sortieren/Filtern (0.9.5)
- Material: Suchfeld + Typfilter (audio/bilder) + Sortierung.
- Auswahl: Suchfeld + Typfilter.
- Letzte Nacht: Suchfelder für Quarantäne und Ausgaben.

## Favoriten (0.9.6)
- Werkzeugkasten-Tab verwaltet Favoriten (Bilder/Logos) als Referenzen.
- Datei: user_data/favorites/favorites.json (schema_version=1).
- Funktionen: hinzufügen, entfernen, Stern, Tags, Suche, Tagfilter.

## Einstellungen-Editor (0.9.7)
- Neuer Tab 'Einstellungen' im Tool.
- Editierbar: Watchfolder, relative User-Ordner, Audio-Fades/Bitraten/Samplerate, Dateinamen-Vorlagen.
- Buttons: Speichern, Standard wiederherstellen, Pfade testen.
- Vorschau Dateiname wird live aktualisiert.

## Maintenance / Cleanup (0.9.8)
- Script: app/maintenance.py
- Läuft automatisch beim Start und vor Automatik.
- Rotiert logs/activity_log.jsonl + logs/debug.log, räumt cache/thumbs + cache/temp_renders auf.
- Löscht alte reports nach reports_keep_days.
- Schützt Exports/Library/Projects/Favorites (werden nie gelöscht).

## Quarantäne Tagesliste als UI (0.9.9)
- Neuer Tab: Quarantäne-Aufträge (heute)
- Tabelle: Status, Datei, Grund, Versuche, Aktion
- Buttons: Neu (Ton Safe), Quelle ersetzen (Hinweis), Zurückstellen, Erledigt
- Ziel: Quarantäne komplett im Tool abarbeiten.

## Werkbank Export (0.9.10)
- GUI kann Standbild+Audio direkt aus Auswahl exportieren (auch Stapel, 1 Bild für alle).
- Optional: Lauftext (drawtext) + Logo (overlay) + Schwarz/Weiß.
- Script: app/manual_export.py, Wrapper: tools/run_workbench_export.sh
- Output in exports/YYYY-MM-DD/

## Batch-Zuweisung (0.9.11)
- Werkbank: Bild-Zuweisung für Stapel (1 Bild für alle / der Reihe nach / manuell).
- Manuell: Dialog mit Zeilenformat 'audio | bild'.

## Hilfe-Center (0.9.12)
- Neuer Tab 'Hilfe' im Tool.
- Quelle: portable_data/config/HELP_CENTER.md
- Suche im Hilfetext + Button 'Hilfe-Datei öffnen'.

## Barriere-Labels (0.9.13)
- In main.py werden zentrale Widgets mit AccessibleName/Description versehen.
- Ziel: Screenreader-Kompatibilität und Tastaturführung.

## Schonmodus (0.9.14)
- Implementiert als Thread-Limit für FFmpeg (Qualität bleibt gleich).
- Settings: config/settings.json → performance.eco_mode / eco_threads / normal_threads.
- Script: tools/toggle_schonmodus.sh (schaltet eco_mode an/aus).

## Must-Pass Suite (0.9.15)
- Läuft über tools/run_must_pass.sh
- Prüft Compile, Werkbank (normal+Schonmodus), Automatik (ok + Quarantäne-Fall), Tonprüfung.
- Ergebnis: user_data/reports/must_pass_*.json

## Preflight / Werkstatt-Check (0.9.16)
- Modul: app/preflight.py
- Prüft ffmpeg/ffprobe, Watchfolder, Schreibrechte, freien Speicher, Font.
- UI: Banner + Details.

## Entwicklungsstatus
- Datei: portable_data/config/DEVELOPMENT_STATUS.md
- Wird pro Iteration aktualisiert (Fertig/Offen/Prozent/Nächster Schritt).

## Edgecase-Härtung (0.9.18)
- Werkbank: Fallback auf sicheren Exportordner bei Schreibproblemen.
- Fehlendes Logo wird übersprungen.
- Preflight: fehlende Schrift deaktiviert Lauftext.
- Preflight: Watchfolder wählen & speichern.

## Audit (0.9.19)
- Entfernt/umbenannt: Variablen-Kommentare und Variablen-Wortlaut in Tooltips.
- Must-Pass Suite nutzt Fast-Test Modus (MODULTOOL_FAST=1) für schnelle, stabile CI-ähnliche Checks.
