# Modultool Video-Werkstatt (videotool-ffmpeg)

## Kurzüberblick
Dieses Projekt verarbeitet Videos mit FFmpeg (Video-Werkzeug). Der Fokus liegt auf **Datensicherheit**, **Barrierefreiheit (Zugänglichkeit)** und **klaren Prüfungen** vor dem Start. Die Start-Routine installiert Abhängigkeiten (Dependencies = benötigte Zusatzpakete) automatisch, zeigt klare Hinweise und schreibt Logs (Protokolle), damit Fehler schnell gefunden werden.

## Entwicklungsfortschritt
- Stand: **95%** (74 von 78 Punkten erledigt).
- Offene Punkte (nummeriert, wird jede Iteration aktualisiert):
  1) main.py modularisieren: UI (Benutzeroberfläche) in klare Klassen trennen.
  2) Barrierefreiheit & UI-Integration vervollständigen: Quarantäne-Tagesliste editierbar, Plugin-Schnittstelle (Erweiterungs-Anschluss) für Presets.
  3) Selftest (automatische Prüfung) um Bitraten-, Fehler- und Großdatei-Szenarien erweitern.
  4) Performance (Leistung) optimieren: parallele Audio-Verarbeitung einführen.

## Schnellstart (einfach & sicher)
1) **Starten**
   ```bash
   tools/start.sh
   ```
   *Die Start-Routine richtet Python (Programmiersprache) und Abhängigkeiten ein und führt den Werkstatt-Check (Startprüfung) aus.*

2) **Automatik (CLI) nutzen**
   ```bash
   tools/run_automation.sh
   ```

3) **Selftest (Automatische Prüfung)**
   ```bash
   tools/run_selftest.sh
   ```

## Vollautomatische Prüfungen & Abhängigkeiten
- **Abhängigkeiten werden automatisch installiert** (Python-Umgebung + Pakete), inkl. Nutzerfeedback bei Problemen.
- **Werkstatt-Check (Preflight = Startprüfung)** prüft u. a. FFmpeg, Speicherplatz und notwendige Einstellungen.
- **Start-Routine löst Abhängigkeiten automatisch** (auto-fix = selbstständig reparieren) und meldet **klar verständlich**, was funktioniert hat oder wo Hilfe nötig ist.

## Qualitäts- und Formatprüfungen (Codequalität)
Für eine automatische Qualitätsprüfung gibt es ein eigenes Skript:
```bash
tools/run_quality_checks.sh
```
Es prüft u. a.:
- Python-Compile (schneller Syntax-Check)
- Shell-Skripte (Bash-Check)
- Marker-Scan (keine Platzhalter wie TODO/FIXME in .py/.sh)
- Must-Pass Suite (wenn FFmpeg vorhanden ist)
- Format-Check (Formatprüfung) mit **ruff** (Code-Format und Stilprüfung)

**Vollständiger Release-Check (alles in Reihenfolge):**
```bash
tools/run_release_checks.sh
```
*Der Release-Check führt Compile, Bash-Check, Qualitäts-Checks, Must-Pass und Release-Builds aus.*

*Hinweis:* Die Skripte richten eine venv (virtuelle Umgebung) ein und installieren notwendige Prüf-Tools automatisch.

## CI (GitHub Actions = automatischer Build-Server)
- **Pfad korrekt:** Workflows liegen unter `.github/workflows/`.
- **CI-Workflow:** `ci.yml` führt **Qualitäts-Checks** automatisch aus (Compile, Bash-Check, Marker-Scan, Format-Check, Must-Pass).
- **Release-Workflow:** `release.yml` baut ZIP + .deb und erstellt ein Release bei Tags `v*`.

## Tests & Checks
- **Must-Pass Suite (Pflicht)**
  ```bash
  tools/run_must_pass.sh
  ```
- **Selftest (empfohlen für Funktionsprüfung)**
  ```bash
  tools/run_selftest.sh
  ```

## Struktur & Wartbarkeit (einheitliche Standards)
- `app/` → Programmlogik (Code)
- `tools/` → Start- und Prüfskripte (Werkzeuge)
- `portable_data/` → **Variable Daten** (Logs, Cache, Reports)
- `portable_data/config/` → **Konfiguration** (Settings, Manifest, Status)
- `app/io_utils.py` → **Einheitliche JSON-IO** (atomic writes = atomar/sicher speichern, inkl. Lock)

*Ziel:* Systemdateien (Code) sind getrennt von variablen Daten (Logs/Cache). Das erleichtert Backups, Updates und Wartung.

**Projektverzeichnis & Dateien (finaler Überblick):**
- Siehe `portable_data/config/PROJECT_STRUCTURE.md` (klare Liste der Ordner und Dateien).

## Versionierung (Regel)
- **Semantische Versionierung (SemVer)**: MAJOR.MINOR.PATCH
  - **MAJOR**: breaking change (nicht abwärtskompatibel)
  - **MINOR**: neue Funktion (abwärtskompatibel)
  - **PATCH**: Bugfix oder Doku-Update
- **Pflicht-Update bei jedem Release:**
  - `portable_data/config/manifest.json` → `version` + `build_date`
  - `portable_data/config/CHANGELOG.md` → Ein Absatz pro Release
  - `portable_data/config/DEVELOPMENT_STATUS.md` → Fortschritt + nächster Schritt

## Barrierefreiheit & Themes
- Mehrere **Hochkontrast-Themes** sind verfügbar (besserer Kontrast = bessere Lesbarkeit).
- Kontrast-Checks sind automatisiert in der Must-Pass Suite integriert.
- **Perfektes Kontrastverhalten:** Themes werden geprüft, ungültige Auswahl fällt auf sicheren Standard zurück.

## Logging & Debugging (Fehlersuche)
- Logs (Protokolle) liegen unter `portable_data/logs/`.
- Wichtige Dateien: `activity_log.jsonl`, `debug.log`.
- Die Wartung rotiert Logs automatisch (schützt vor übervollen Dateien).
- Debug-Modus (Fehlersuche): starte mit `MODULTOOL_DEBUG=1 tools/start.sh` (Debug = mehr Details im Log).
- Längere Fehlersuche (Debug-Log direkt speichern):
  ```bash
  MODULTOOL_DEBUG=1 tools/start.sh | tee start.log
  ```
  *`tee` speichert den Log (Protokoll) in `start.log` und zeigt ihn gleichzeitig im Terminal.*

### Wenn der Start auf neuen Systemen hakt (Checkliste für Laien)
1) **Fehlertext notieren** (genau so wie angezeigt).
2) **Debug-Log speichern**:
   ```bash
   MODULTOOL_DEBUG=1 tools/start.sh | tee start.log
   ```
3) **System prüfen** (einfach):
   - Ist **FFmpeg** (Video-Werkzeug) installiert?
   - Ist **Python 3.9+** (Programmiersprache) verfügbar?
   - Ist genug **Speicherplatz** frei?
4) **Log teilen**: `start.log` an Support/Technik weitergeben.
5) **Sicherer Standard**: Neustart nach Installation/Update der fehlenden Abhängigkeiten.

## Linux-Konformität & Berechtigungen
- Alle Skripte in `tools/` sind ausführbar (Linux-Standard).
- Falls Rechte fehlen, einmalig setzen:
  ```bash
  chmod +x tools/*.sh
  ```

## Hinweise für macOS & Windows (experimentell)
- Die `tools/*.sh` Skripte sind für Linux ausgelegt. Auf macOS/Windows bitte **Python direkt** verwenden.
- **Abhängigkeiten installieren** (Beispiel, manuell):
  ```bash
  python3 -m venv portable_data/.venv
  portable_data/.venv/bin/pip install -r app/requirements.txt
  ```
  *Unter Windows entspricht der Pfad meist `portable_data\\.venv\\Scripts\\pip.exe`.*
- **Starten (GUI)**:
  ```bash
  portable_data/.venv/bin/python app/main.py
  ```
- **FFmpeg installieren** (Pflicht): z. B. via Homebrew (`brew install ffmpeg`) oder Chocolatey (`choco install ffmpeg`).

## Weiterführende Laien-Tipps (einfach erklärt)
- **Wenn FFmpeg fehlt:** Installiere es über den Paketmanager deiner Linux-Distribution.
- **Wenn zu wenig Speicher frei ist:** Alte Export-Dateien oder Cache löschen.
- **Wenn die Vorschau langsam ist:** Schonmodus (Eco-Modus) aktivieren.
- **Wenn die Schrift zu klein wirkt:** System-Schriftgröße erhöhen oder High-Contrast (Hochkontrast) Theme wählen.
- **Wenn Format-Checks fehlschlagen:** `tools/run_quality_checks.sh` starten, dann Hinweise im Terminal lesen.

## Release-Checkliste (Release = Veröffentlichung)
Für den Release fehlen typischerweise:
- ZIP bauen und Start auf einem frischen System testen.
- .deb bauen und Installation testen.
- Must-Pass Suite auf Zielsystem ausführen.

*Details:* `portable_data/config/DEVELOPMENT_STATUS.md` zeigt den aktuellen Stand.

## Support & nächste Schritte
- Prüfe `todo.txt` für geplante Verbesserungen.
- Lies `portable_data/config/DEVELOPMENT_STATUS.md` für den aktuellen Entwicklungsstand.
