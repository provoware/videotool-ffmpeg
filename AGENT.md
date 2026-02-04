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

## 0.1) Release-Finalisierung (finale Freigabe)
Ziel: Release sauber abschließen, ohne Risiko. Alles ist automatisiert, nachvollziehbar und barrierefrei.

### A) Release-Freeze (Stabilitätsfenster)
- Keine neuen Features, nur Fixes und Dokumentation.
- Alle Änderungen klein halten (max. 3 Fixes oder 3 Verbesserungen).
- Jede Änderung braucht einen belegbaren Grund (Datei + Abschnitt).

### B) Vollautomatische Start-Routine (Autostart)
Die Start-Routine muss alles prüfen, reparieren und dem Nutzer klare Rückmeldungen geben.

**Pflicht-Ablauf (mit einfachen Worten + Begriffserklärung):**
1. `tools/start.sh` starten (Start-Routine = automatischer Start-Check).
2. Abhängigkeiten prüfen und installieren (Dependencies = Zusatzpakete).
3. Status und nächste Schritte zeigen (Feedback = verständliche Rückmeldung).
4. Ergebnis in Log-Datei schreiben (Log = Protokoll).

### C) Release-Checks (vollautomatisch)
Alle Checks laufen als feste Reihenfolge (keine Ausnahmen):
```bash
python3 -m py_compile app/*.py
bash -n tools/*.sh
tools/run_quality_checks.sh
tools/run_must_pass.sh
tools/build_release.sh
```
- Jeder Check zeigt **klaren Erfolg** oder **klaren Fehler**.
- Fehler werden in einfachen Worten erklärt (Fachbegriff in Klammern).
- Effizienz: Wenn `tools/run_release_checks.sh` genutzt wird, darf die Must-Pass Suite in `tools/build_release.sh` per `MODULTOOL_SKIP_MUST_PASS=1` übersprungen werden, um Doppelprüfungen zu vermeiden.

### D) Packaging-Validierung
- ZIP und .deb müssen bauen.
- Portable-Template wird nach `~/.local/share/modultool_portable` kopiert.
- Ergebnis wird geprüft und protokolliert.

### E) Abschluss-Block (Dokumentation)
- `CHANGELOG.md`: Ein Absatz pro Release.
- `manifest.json`: Version bump + build_date.
- `DEVELOPMENT_STATUS.md`: Fortschritt + nächster Schritt.

---

## 0.2) Barrierefreiheit & klare Sprache (Pflicht)
- Einfache Sprache, Fachbegriffe in Klammern erklären.
- Kontraste prüfen (Kontrast = Lesbarkeit).
- Themes müssen immer verfügbar sein (hochkontrast dunkel/hell + dämmerung).
- Jede Nutzeraktion muss eine klare Rückmeldung geben (Erfolg/Fehler).

---

## 0.3) Vollautomatische Tests & Qualität (Pflicht)
- **Codequalität**: `tools/run_quality_checks.sh` (ruff check + ruff format --check).
- **Funktion**: `tools/run_must_pass.sh`.
- **Struktur**: `bash -n tools/*.sh` und `python3 -m py_compile app/*.py`.
- **Marker-Scan**: Kein TODO/FIXME/placeholder/Platzhalter in `.py`/`.sh`.

---

## 0.4) Struktur-Regeln für Wartbarkeit
Ziel: Trenne Logik, Systemdateien und variablen Daten klar.
- `app/` = Programm-Logik (Logik = Kernfunktionen).
- `tools/` = Skripte/Automationen (Skripte = Hilfsprogramme).
- `portable_data/config/` = feste Konfiguration (Config = feste Einstellungen).
- `portable_data/` = variable Nutzerdaten (Daten = veränderliche Inhalte).
- Nie mischen: Logik nicht in Config, Config nicht in Logs.

---

## 0.5) Input/Output-Validierung (Pflicht)
- Jede Funktion prüft Eingaben (Input = Nutzereingabe).
- Jede Funktion bestätigt Ergebnis (Output = Ergebnis/Status).
- Fehler immer mit nächstem Schritt erklären.

---

## 0.6) Debugging & Logging (Pflicht)
- Debug-Modus muss klar schaltbar sein (Debug = Fehlersuche).
- Logs trennen: Nutzer-Feedback vs. Entwickler-Log.
- Kein Silent-Fail: jede Abweichung wird protokolliert und erklärt.

---

## 0.7) Laien-Tipps (weiterführend)
- Wenn etwas scheitert: zuerst den Standardweg anbieten.
- Bei Fehlern: „Jetzt reparieren“, „Sicherer Standard“, „Details“ anbieten.
- Tests sind wie TÜV: erst bestehen, dann ausliefern.

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
