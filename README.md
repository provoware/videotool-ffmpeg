# Modultool Video-Werkstatt (videotool-ffmpeg)

## Kurzüberblick
Dieses Projekt verarbeitet Videos mit FFmpeg (Video-Werkzeug). Der Fokus liegt auf **Datensicherheit**, **Barrierefreiheit (Zugänglichkeit)** und **klaren Prüfungen** vor dem Start. Die Start-Routine installiert Abhängigkeiten (Dependencies = benötigte Zusatzpakete) und zeigt klare Hinweise, wenn etwas fehlt.

## Schnellstart (einfach & sicher)
1) **Starten**
   ```bash
   tools/start.sh
   ```
   *Die Start-Routine richtet Python (Programmiersprache) und Abhängigkeiten ein und führt den Werkstatt-Check aus.*

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

*Hinweis:* Das Skript richtet eine venv (virtuelle Umgebung) ein und installiert notwendige Prüf-Tools automatisch.

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
- `app/paths.py` → zentrale Pfade (Paths = Speicherorte) für **Portable-Daten**
- `tools/` → Start- und Prüfskripte (Werkzeuge)
- `portable_data/` → **Variable Daten** (Logs, Cache, Reports)
- `portable_data/config/` → **Konfiguration** (Settings, Manifest, Status)

*Ziel:* Systemdateien (Code) sind getrennt von variablen Daten (Logs/Cache). Das erleichtert Backups, Updates und Wartung.

## Barrierefreiheit & Themes
- Mehrere **Hochkontrast-Themes** sind verfügbar.
- Kontrast-Checks sind automatisiert in der Must-Pass Suite integriert.

## Logging & Debugging (Fehlersuche)
- Logs (Protokolle) liegen unter `portable_data/logs/`.
- Wichtige Dateien: `activity_log.jsonl`, `debug.log`.
- Die Wartung rotiert Logs automatisch (schützt vor übervollen Dateien).
- Debug-Modus (Fehlersuche): starte mit `MODULTOOL_DEBUG=1 tools/start.sh` (Debug = mehr Details im Log).

## Linux-Konformität & Berechtigungen
- Alle Skripte in `tools/` sind ausführbar (Linux-Standard).
- Falls Rechte fehlen, einmalig setzen:
  ```bash
  chmod +x tools/*.sh
  ```

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
