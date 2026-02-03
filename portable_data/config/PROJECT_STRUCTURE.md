# Projektverzeichnis & Dateien (finaler Überblick)

Stand: 2026-02-20T10:00:00Z

Ziel: **klar trennen** zwischen Systemdateien (Code) und variablen Daten (veränderliche Inhalte). So bleiben Updates sicher und Daten gehen nicht verloren.

## Schnellüberblick (Baum)
```
/ (Projektwurzel)
├─ app/                        # Programmlogik (Kernfunktionen)
├─ assets/                     # mitgelieferte Dateien (statisch)
├─ tools/                      # Skripte & Automationen (Start/Checks/Builds)
├─ portable_data/              # variable Daten + Konfiguration
│  ├─ config/                  # feste Konfiguration (Settings, Manifest, Status)
│  ├─ user_data/               # Nutzerdaten (Exports, Library, Reports)
│  ├─ logs/                    # Protokolle (activity_log.jsonl, debug.log)
│  └─ cache/                   # Thumbnails + temporäre Renderdaten
├─ README.md                   # Projektübersicht
└─ todo.txt                    # laufende Aufgabenliste
```

## Wichtige Ordner (einfach erklärt)
- `app/` → **Logik** (Kern-Code). Hier liegt die gesamte Programmlogik.
- `tools/` → **Werkzeuge** (Skripte). Start, Prüfungen, Builds (ZIP/.deb) laufen hier.
- `portable_data/` → **Variable Daten** (ändern sich im Betrieb).
- `portable_data/config/` → **Feste Konfiguration** (Settings, Texte, Themes, Versionen).
- `portable_data/user_data/` → **Nutzerdaten** (Exports, Bibliotheken, Reports).

## Konfiguration (portable_data/config)
- `manifest.json` → Version, Features, Mindestanforderungen.
- `settings.json` → globale Einstellungen (Pfade, Audio, Performance).
- `automation_rules.json` → Zeitplan und Scan-Regeln.
- `themes.json` → Themes (Hochkontrast dunkel/hell + Dämmerung).
- `texte_de.json` / `texte_en.json` → UI-Texte (Deutsch/Englisch).
- `CHANGELOG.md` → Änderungsverlauf pro Release.
- `DEVELOPMENT_STATUS.md` → Fortschritt + nächster Schritt.
- `DEVELOPER_MANUAL.md` → Entwicklerdoku im Tool.
- `HELP_CENTER.md` → Hilfe-Center-Inhalte.
- `README.txt` → kurze Nutzeranleitung.
- `PROJECT_STRUCTURE.md` → diese Datei (finaler Überblick).

## Nutzerdaten (portable_data/user_data)
- `exports/` → fertige Ausgaben (Ergebnisse).
- `library/audio/` → verwendete Audios.
- `library/images/` → verwendete Bilder.
- `staging/` → Zwischenablage (Input-Dateien bis zur Validierung).
- `quarantine/` → Problemfälle.
- `quarantine_jobs/` → Quarantäne-Aufträge pro Tag.
- `reports/` → Arbeitsberichte (run_*.json).
- `trash/` → Papierkorb (erst nach validiertem Commit).

## Regeln (wichtig)
- **Systemdateien nie mit Nutzerdaten mischen.**
- **Alle variablen Daten bleiben in `portable_data/`.**
- **Konfiguration (Config) bleibt stabil, Logs/Cache sind austauschbar.**
- **Jede Funktion validiert Input (Eingabe) und bestätigt Output (Ergebnis).**
