# AGENTS.md – Modultool Video-Werkstatt (Agenten-Regeln)

Ziel: Release robuster machen, ohne Chaos. Jeder Durchlauf ist klein, messbar, rückverfolgbar.

---

## 0) Arbeitsmodus (Pflicht)
Jede Iteration besteht aus exakt diesen Schritten:

1) **Codeanalyse (Pflicht)**
   - Fehler, Inkonsistenzen, riskante Stellen finden.
   - Konkrete Fundstellen nennen (Datei + Funktion/Abschnitt).
   - Kein Umbau ohne belegbaren Grund.

2) **Kleinster sinnvoller Schritt (Pflicht)**
   - Genau 3 Optimierung oder 3 Bugfix pro Iteration.
   - Keine Nebenbaustellen.
   - Keine „schon mal mitmachen“-Änderungen.

3) **Prüfen + Dokumentieren (Pflicht vor Ausgabe)**
   - Python Compile: `python3 -m py_compile app/*.py`
   - Format-Check (Formatprüfung): `tools/run_quality_checks.sh` (enthält ruff check + ruff format --check)
   - Marker-Scan: kein `TODO`, `FIXME`, `placeholder`, `Platzhalter` in `.py`/`.sh`
   - Must-Pass Suite: `tools/run_must_pass.sh` (wenn ffmpeg vorhanden)
   - Ergebnis dokumentieren (kurz)
   - `CHANGELOG.md` aktualisieren (ein Absatz)
   - `manifest.json` Version bump
   - `DEVELOPMENT_STATUS.md` Fortschritt + nächster Schritt

---

## 1) Nicht verhandelbare Regeln
1) **Keine Qualitäts-Reduktion**
   - Schonmodus steuert nur Threads/Last. Keine Bitrate/CRF/Format-Senkung.
2) **Keine Datenverluste**
   - Zwischenablage → Temp → Validierung → Commit bleibt.
3) **Kein Silent-Fail**
   - Jede Abweichung: Report + UI-Hinweis + nächste Aktion (Button/Schritt).
4) **Keine Platzhalter im Code**
   - Keine Markerwörter und kein „kommt später“-Text im Code.
5) **Laienführung**
   - Jeder Blocker braucht: „Jetzt reparieren“, „Sicherer Standard“ oder „Details“.

---

## 2) Release-Gates (müssen grün sein)
### 2.1 Code
- `python3 -m py_compile app/*.py`
- `bash -n tools/*.sh`
- Marker-Scan (siehe test.yml)
- Format-Check (Formatprüfung) via `tools/run_quality_checks.sh`

### 2.2 Funktion
- `tools/run_must_pass.sh` liefert pass (oder skip, wenn ffmpeg nicht vorhanden)
- Preflight ok oder klare UI-Reparaturpfade

### 2.3 Packaging
- ZIP baut
- .deb baut
- Launcher kopiert Template nach `~/.local/share/modultool_portable`

---

## 3) Der kleinste nächste Schritt (Standard-Auswahl)
Wenn mehrere Dinge gleichzeitig möglich wären, ist die Reihenfolge:
1) Absturz/Compile-Fix
2) Datenverlust-Risiko
3) Audioqualität/Validierung
4) UI-Blocker für Laien
5) Performance/Last (ohne Qualitätsänderung)
6) Komfort/Politur

---

## 4) Format für Statusausgabe (Pflicht)
Am Ende jeder Iteration:
- Version: x.y.z
- Änderung: 1 Satz
- Prüfen: compile ok, marker-scan ok, must-pass ok/skip
- Nächster Schritt: 1 Satz

---

## 5) Lokale Schnellchecks
```bash
bash -n tools/*.sh
python3 -m py_compile app/*.py
tools/run_must_pass.sh
