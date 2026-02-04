# AGENTS.md – Modultool Video-Werkstatt (Agenten-Regeln)
Ziel: Release robuster machen, ohne Chaos. 
Jeder Durchlauf ist klein, messbar, rückverfolgbar.
## 0) Arbeitsmodus (Pflicht)
Jede Iteration besteht aus exakt diesen Schritten und den Zwangsvorgaben:

Basisvorgabe:) **Codestandards (Pflicht)**
   - Voll Modular, pluginfähig, erweiterbar, optimal Getrennte Logik - regel festhalten und standards definieren.
   - deutsche Toolsprache im Tool und CLI mit deutschen Aliasen
   - Maximal 1200 Zeilen pro Datei 
   - Code kurz aber verständlich und eindeutig, hilfreich kommentieren.
   - bei updates von codeteilen exakte und professionelle, vallidierende, perfekt versionierende und den erfolg dokumentierende Bereichsgeneue Patches,
     dieser wird zuvor geplant mit stelle, versionsprüfung, konsistenter implementierung und fix und vallidierung auf fehlerfreiheit.
   - todo.txt + README.txt + 
   - Patches zuvor in Liste sammeln, mit genauen stellen und patch, als checkliste, nach der planung umsetzung, exakt im bereich um code arm zu arbeiten. fix, vallidierung auf erfolg und doku!
   - Leerdummydatei immer sofort erzeigen und mit kurzinfo mit 3 wörtern in erster zeile , dann registrieren
   - Funktionen und Elemente wiederverwendbar machen
   - Linux-konforme ausrichtung 
   - keine endlosschleifen
   - hoch detailliertes und eindeutiges Debugging mit Anzeige von Lösungen oder direkt mit Buttons Lösung anbieten
   - logging einfach und verständlich und eindeutig mit hilfreichen tip
   - Exit führt nie ins Nichts, Fehler werden immer mit Lösung oder funktion oder sonstigem weiterführenden Beantwort, keine Abrüche, Präventive Berücksichtigung
   - Alles bekommt seine selfrepair Elemente
   - Codequalität hochhalten, Fehlerhandling intelligent, tolerant und selbstreparierend
    
1) **Codeanalyse (Pflicht)**
   - Fehler, Inkonsistenzen, riskante Stellen finden.
   - Konkrete Fundstellen nennen (Datei + Funktion/Abschnitt/Zeile).
   - Kein Umbau ohne belegbaren Grund.
   - Keine Nebenbaustellen.

2) **Kleinster sinnvoller Schritt (Pflicht)**
   - Genau 3+1 Optimierung (3 optimierungen aus todo und 1 optimierung aus LaienTauglichkeitsoptimierung und eine Optimierung in einem Hilfetext, Beschreibung oder Ähnlichem) und 3 Bugfix oder 3 Hilfeelemente verbessern pro Iteration.
   - Keine „schon mal mitmachen“-Änderungen, kein anfassen von anderen als den geplanten Dateien, kein Code zerstören der schon tadellos funktioniert.
   - Perfekt organisierte Versionierung mit JSON-Versionsverwaltung

3) **Prüfen + Dokumentieren (Pflicht vor Ausgabe)**
   - Format-Check (Formatprüfung): `tools/run_quality_checks.sh` (enthält ruff check + ruff format --check)
   - Marker-Scan: `placeholder`, `Platzhalter` in allen dateien, genauso wie nach `TODO` , `FIX` alle Fundstellen registrieren und in `registry.json` mit aufnehmen
   - Ergebnis dokumentieren (kurz) - Schritt Nr. + Aspekt/Registrieren 
   - `CHANGELOG.md` aktualisieren (ein Absatz)
   - `manifest.json` globale Standards, Standards, Vorgaben
   - `ENTWICKLUNGS_STATUS.md` Fortschritt + nächster Schritt + Prozentzahl Entwicklungsfortschritt
## 0.1) Release-Finalisierung (finale Freigabe)
Ziel: Release sauber abschließen, ohne Risiko. 
      Alles ist automatisiert, nachvollziehbar und barrierefrei.
      Mit perfekter und detaillierter professioneller Entwicklerdoku inklusive Befehls und Syntxglossar am Ende.
### A) Release-Freeze (Stabilitätsfenster)
- Keine neuen Features, nur Fixes, Vervollständigung und Dokumentation.
- Alle Änderungen klein halten (aber wenn möglich immer vollständig und ohne Auslassungen).
- Jede Änderung braucht einen belegbaren Grund (Datei + Abschnitt/Zeilenbereich).
### B) Vollautomatische Start-Routine (Autostart)
Die Start-Routine muss alles Autonom und vollautomatisch prüfen, reparieren und dem Laien-Nutzer klare Rückmeldungen geben.
**Pflicht-Ablauf (mit einfachen Worten + Begriffserklärung):**
1. `start.sh` starten (Start-Routine = automatischer Start-Check).
2. alle Abhängigkeiten, auch OS oder Zusatztools prüfen und vollautomatisch installieren (Dependencies = Zusatzpakete).
3. Status und nächste Schritte zeigen und kurze begründung 5 worte (Feedback = verständliche Rückmeldung).
4. Ergebnis in Log-Datei schreiben (Log = Protokoll , bleibt persistent erhalten als Entwicklungschronologie).
### C) Release-Checks (vollautomatisch)
Alle Checks laufen als feste Reihenfolge (keine Ausnahmen):
- Jeder Check zeigt **klaren Erfolg** oder **klaren Fehler**.
- Fehler werden in einfachen Worten erklärt (Fachbegriff in Klammern).
### D) Packaging-Validierung
- Ergebnis wird geprüft und protokolliert.
### E) Abschluss-Block (Dokumentation)
- `CHANGELOG.md`: Ein Absatz pro Release.
- `manifest.json`: Version bump + build_date.
- `DEVELOPMENT_STATUS.md`: Fortschritt + nächster Schritt.
## 0.2) Barrierefreiheit & klare Sprache (Pflicht)
- Einfache Sprache, Fachbegriffe in Klammern erklären in deutschen Worten.
- Kontraste prüfen (Kontrast = Lesbarkeit, auch für Sehschwache).
- Themes müssen immer verfügbar sein (carmouflage + dunkel/hell + sonnendämmerung).
- Jede Nutzeraktion muss eine klare Rückmeldung geben (Erfolg/Fehler).
- Maximale Flexibilität in zoom von schrift oder bereichen, maximale flexibilität in skalierung und positionierung
- Maximale Nutzerfreundlichkeit/Interaktivität und Transparenz in Information und Status
## 0.3) Vollautomatische Tests & Qualität (Pflicht)
- **Codequalität**: `tools/run_quality_checks.sh` (ruff check + ruff format --check).
- **Marker-Scan**: Kein TODO/FIXME/placeholder/Platzhalter in in allen Dateien immer Fund registrieren in todo
## 0.4) Struktur-Regeln für Wartbarkeit
Ziel: Trenne Logik, Systemdateien und variablen Daten klar.
- `app/` = Programm-Logik (Logik = Kernfunktionen).
- `tools/` = Skripte/Automationen (Skripte = Hilfsprogramme).
- `data/config/` = feste Konfiguration (Config = feste Einstellungen).
- `user/` = variable Nutzerdaten (Daten = veränderliche Inhalte).
- Nie mischen: Logik nicht in Config, Config nicht in Logs.
## 0.5) Input/Output-Validierung (Pflicht)
- Jede Funktion prüft Eingaben (Input = Nutzereingabe).
- Jede Funktion bestätigt Ergebnis (Output = Ergebnis/Status).
- Fehler immer mit nächstem Schritt erklären.
## 0.6) Debugging & Logging (Pflicht)
- Debug-Modus muss klar schaltbar sein (Debug = Fehlersuche).
- Logs trennen: Nutzer-Feedback vs. Entwickler-Log.
- Kein Silent-Fail: jede Abweichung wird protokolliert und erklärt.
## 0.7) Laien-Tipps (weiterführend)
- Wenn etwas scheitert: zuerst den Standardweg anbieten.
- Bei Fehlern: „Jetzt reparieren“, „Sicherer Standard“, „Details“ anbieten. Empfohlene option kenntlich machen.
- Tests sind wie TÜV: erst bestehen, dann ausliefern.
## 1) Nicht verhandelbare Regeln
1) **Keine Qualitäts-Reduktion**
2) **Keine Datenverluste**
   - Zwischenablage → Temp → Validierung → Commit bleibt.
3) **Kein Silent-Fail**
   - Jede Abweichung: Report + UI-Hinweis + nächste Aktion (Button/Schritt).
4) **Keine Platzhalter im Code**
   - Keine Markerwörter und kein „kommt später“-Text im Code.
5) **Laienführung**
   - Jeder Blocker braucht: „Jetzt reparieren“, „Sicherer Standard“ oder „Details“.
---
### 2.3 Packaging
- klick_und_start.sh autoinstaller_setup.sh und was in vorgaben entschieden wird
---
## 3) Der kleinste nächste Schritt (Standard-Auswahl)
Wenn mehrere Dinge gleichzeitig möglich wären, ist die Reihenfolge:
## 4) Format für Statusausgabe (Pflicht)
Am Ende jeder Iteration:
- Version: x.y.z
- Änderung: 1 Satz
- Prüfen: Soll/Ist=Plan, marker-scan ok, ok/skip
- Nächster Schritt: 1 Satz + 5 detailwörter
---
## 5) Lokale Schnellchecks
- je nach Frameworks oder Architektur optimal selbst ermitteln und implementieren, aber keine eigenen Fallen bauen
