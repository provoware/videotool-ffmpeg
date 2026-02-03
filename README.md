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

*Ziel:* Systemdateien (Code) sind getrennt von variablen Daten (Logs/Cache). Das erleichtert Backups, Updates und Wartung.

## Barrierefreiheit & Themes
- Mehrere **Hochkontrast-Themes** sind verfügbar.
- Kontrast-Checks sind automatisiert in der Must-Pass Suite integriert.

## Logging & Debugging (Fehlersuche)
- Logs (Protokolle) liegen unter `portable_data/logs/`.
- Wichtige Dateien: `activity_log.jsonl`, `debug.log`.
- Die Wartung rotiert Logs automatisch (schützt vor übervollen Dateien).

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

## Support & nächste Schritte
- Prüfe `todo.txt` für geplante Verbesserungen.
- Lies `portable_data/config/DEVELOPMENT_STATUS.md` für den aktuellen Entwicklungsstand.
