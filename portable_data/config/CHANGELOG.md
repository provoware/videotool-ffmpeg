# CHANGELOG

## 1.0.37
- Quarantäne-Tabelle: Inline-Bearbeitung für Status, Grund und Empfehlung mit Validierung.
- UI-Logik: Quarantäne-Tab in einen eigenen Controller modularisiert.
- Rückmeldungen: Statusleiste bestätigt Quarantäne-Updates klar und verständlich.

## 1.0.38
- CI: GitHub Actions liegen korrekt unter .github/workflows und führen Qualitäts-Checks automatisch aus.
- IO: Atomic JSON Writes über einen zentralen IO-Helper für konsistente, sichere Schreibvorgänge.
- Locking: Single-Writer-Locks für Settings und Quarantäne-Listen verhindern konkurrierende Schreibzugriffe.

## 1.0.36
- Preflight: Theme-Auswahl wird geprüft und meldet unbekannte Themes mit Empfehlung.
- UI: Theme-Fallback mit Warn-Log sorgt für stabile Barrierefreiheit bei ungültigen Einstellungen.
- Start-Routine: Preflight-Empfehlungen erweitert (Theme-, Pfad- und min_free-Hinweise).

## 1.0.35
- Start-Routine: zentrale Bootstrap-Logik für Python-Abhängigkeiten mit klaren Hinweisen ergänzt.
- Start-Routine: optionaler FFmpeg-Autoinstall per MODULTOOL_AUTO_INSTALL mit verständlicher Rückmeldung.
- Qualitäts-Checks: Bootstrap-Validierung für Dev-Abhängigkeiten und Pflichtpakete vereinheitlicht.

## 1.0.34
- UI-Layout in ein eigenes Modul ausgelagert, damit main.py übersichtlicher bleibt und die Wartbarkeit steigt.

## 1.0.33
- Automatik: Fallback-Bild wird vorab geprüft und fehlende Bilder landen sauber in Quarantäne.
- Automatik: Ungültige Ausgabe-Pfade führen zu Quarantäne statt Abbruch.
- Selftest: fehlende Testassets brechen mit klarer Meldung ab.

## 1.0.32
- Performance: Thread-Anzahl fällt bei 0-Werten dynamisch auf CPU-Kerne zurück (Eco halbiert).
- Reports/Quarantäne-Listen: Schema wird beim Laden normalisiert (Version, Titel, Summary, Status).
- Plattform-Hinweise: Öffnen von Pfaden unterstützt macOS/Windows, README ergänzt Start-Notizen.

## 1.0.31
- Preflight: ungültige Settings (inkl. min_free_mb) blocken overall_ok und liefern settings_ok.
- Quarantäne-Worker: fehlendes ffmpeg/ffprobe wird als klarer Abbruch gemeldet.
- Werkbank: fehlender Font warnt klar, wenn Lauftext übersprungen wird.

## 1.0.30
- Werkbank: FFmpeg-Prüfung mit klarem Hinweis, bevor der Export startet.
- Werkbank: fehlgeschlagene Exporte räumen Temp-Dateien sauber auf und melden den Exit-Code.
- Preflight: Watchfolder-Status zeigt Schreibbarkeit nur bei gültigem Ordner an.

## 1.0.29
- Release: Build-Workflow bündelt ZIP/.deb und Release-Tests in einem Skript.
- Logging: zentrales Log-Modul schreibt Debug- und User-Feedback getrennt mit Log-Leveln.
- Preflight: Settings werden per Schema/Pfad-Checks validiert und Empfehlungen ergänzt.

## 1.0.28
- Automatik: fehlende Batch-Namensvorlage fällt sauber auf Standard zurück.
- Automatik: Lock-Dateien mit PID als Text werden als stale erkannt und bereinigt.
- Maintenance: Log-Rotation trunciert direkt, wenn keine Historie behalten werden soll.

## 1.0.27
- Preflight: Schreibtest nutzt eindeutige Temp-Dateien, damit parallele Checks nicht kollidieren.
- Maintenance: Settings-JSON wird nur als Dict akzeptiert, sonst wird sauber auf Standard zurückgefallen.
- Maintenance: negative MB-Grenzen werden als 0 behandelt, damit Cleanup-Regeln stabil bleiben.

## 1.0.26
- Release: ZIP-Build-Skript ergänzt (lokaler Build mit Version aus Manifest).
- Release: .deb-Build-Skript ergänzt (Template + Launcher, Desktop-Entry).
- Release: Template-Installer kopiert portable Vorlage nach ~/.local/share.

## 1.0.25
- Automatik: Watchfolder wird auch auf Ordner-Status geprüft (klarer Abbruch bei Datei-Pfad).
- Validierung: Ausgabe-Pfad meldet Zielordner sauber, wenn ein Datei-Pfad als Ordner missbraucht wird.
- Werkbank: Audio-Parameter akzeptieren nur positive Werte und fallen sonst sicher auf Standard zurück.

## 1.0.24
- Preflight: ungültige Watchfolder-Eingaben werden klar als Empfehlung gemeldet.
- Werkbank: sichere Fallback-Slugs verhindern leere Dateinamen.
- Werkbank: Audio-Parameter werden robust geparst und warnen bei ungültigen Werten.

## 1.0.23
- Validierung: Ausgabe-Pfade prüfen Schreibrechte und verhindern Ordner-Zielpfade.
- Fehlerberichte: base_data_dir wird validiert, Fehler landen im Debug-Log.
- Preflight: Settings-JSON nur bei gültiger Dict-Struktur übernehmen.

## 1.0.22
- Automatik: Download-Stabilität prüft zusätzlich Hash/MTime, bevor Dateien verarbeitet werden.
- Subprozess-Schutz: FFmpeg-Aufrufe validieren Eingabepfade/Outputs strikt (kein Shell-Injection-Risiko).
- Fehlerberichte: Abbrüche schreiben jetzt einen Report und erscheinen im Dashboard.

## 1.0.21
- Automatik: Abbrüche laufen jetzt über klare Fehlercodes statt SystemExit im Ablauf.
- Quarantäne-Worker: Einstellungen werden vor dem Start validiert und ins Debug-Log geschrieben.
- Quarantäne-Worker: sichere Fallback-Slugs verhindern leere Dateinamen.

## 1.0.20
- Automatik: Lock-Datei mit Timeout und PID-Erkennung gegen parallele Läufe gehärtet.

## 1.0.19
- Automatik: leere Dateinamen-Slugs erhalten einen sicheren Fallback.

## 1.0.18
- Todo-Liste um neue Roadmap-Punkte erweitert.

## 1.0.17
- Preflight: fehlenden Watchfolder automatisch anlegen (Self-Repair).

## 1.0.16
- Maintenance: Dateifehler werden als Warnungen im Summary protokolliert (keine Silent-Fails).

## 1.0.15
- Logging: Ausnahmen in UI/Automation werden konsistent im Debug-Log protokolliert (mit Kontext).

## 1.0.14
- Debug-Log als Datei speicherbar dokumentiert (inkl. einfacher Start-Checkliste).

## 1.0.13
- Start-Routine: Debug-Modus zeigt Pip- und Preflight-Details ohne Log-Unterdrückung.

## 1.0.12
- Preflight: Debug-Log wird stabil geschrieben (Kontextmanager = sicheres Öffnen/Schließen).

## 1.0.11
- Pfadlogik zentralisiert (paths = Speicherorte), weniger Duplikate.
- Qualitäts-Checks: Format-Check (Formatprüfung) mit ruff, Dev-Tools werden automatisch installiert.
- Start-Routine: klarer Hinweis, wenn Abhängigkeiten (Dependencies = Zusatzpakete) nicht installierbar sind.

## 1.0.10
- System-/Automations-Skripte prüfen jetzt Existenz, laufen per QProcess und melden Exit-Code/Fehler mit klaren nächsten Schritten.
- Automatik: Pflicht-Pfade in settings prüfen, klare Aktion im Log bei Fehlern.
- Maintenance: Settings-Ints werden sicher geparst, mit Warnung und Fallback im Summary-Log.


## 1.0.9
- Preflight: Watchfolder-Schreibrecht prüfen und klare Hinweise anzeigen.


## 1.0.8
- Preflight: Debug-Modus mit Log-Leveln und Debug-Logausgabe ergänzt.


## 1.0.7
- Preflight: ungültigen min_free_mb-Wert melden und Standard klar anzeigen.


## 1.0.6
- Preflight: robustes Parsen der Mindest-Speichergrenze, inkl. Fallback bei ungültigen Werten.


## 1.0.5
- Must-Pass Suite: automatischer Kontrast-Check für alle Themes.


## 1.0.4
- Start-Routine: Werkstatt-Check mit klaren nächsten Schritten beim Start.


## 1.0.3
- Werkstatt-Check Details: Klartext-Anzeige mit einfachen Empfehlungen und Status.


## 1.0.2
- Test: Must-Pass Suite prüft automatisch die Thumbnail-Erzeugung aus einer Beispiel-Bilddatei.


## 1.0.1
- Fix: Thumbnails werden wieder korrekt erzeugt und gecacht (get_thumb_pixmap Logik korrigiert).


## 1.0.0
- Release UI-Politur: konsistente Beschriftungen, Standardwerte, Button-Abstände, kontrastreiche Themes.
- Theme-QSS aus themes.json wird geladen (hochkontrast dunkel/hell, dämmerung).
- Zoom-Schrift (ui.zoom_percent) wird angewendet.


## 0.9.19
- Hochschulischer Audit: Variablen-Texte entfernt/umbenannt (keine Variablen im Code).
- Fix: Must-Pass Suite ohne venv-Abhängigkeit + Fast-Test Modus (schnell, deterministisch).
- Fix: FFmpeg loglevel error (weniger Spam), Tests bestehen in <60s.


## 0.9.18
- Portable Härtung: Edgecase-Fallbacks (Exportordner, Fonts, Logo fehlt, Watchfolder setzen).
- Preflight liefert Empfehlungen und deaktiviert Lauftext bei fehlender Schrift.


## 0.9.17
- Entwicklungsstatus-Datei aktualisiert (Listen + Prozent + nächster Schritt).


## 0.9.16
- Paket-Härtung: Preflight/Werkstatt-Check (FFmpeg, Pfade, Speicher, Watchfolder) + UI-Banner.
- Kritische Buttons werden deaktiviert, wenn FFmpeg fehlt.
- Details-Button zeigt vollständige Preflight-Daten.


## 0.9.15
- Release-Testplan: Must-Pass Suite (Werkbank normal/eco, Automatik ok, Quarantäne bei schlechter Bitrate, Compile-Check).
- Script: tools/run_must_pass.sh, Report: user_data/reports/must_pass_*.json


## 0.9.14
- Schonmodus technisch abgesichert: FFmpeg nutzt Threads aus settings.json (Werkbank + Automatik), Qualität bleibt unverändert.
- Neues Modul app/perf.py + Script tools/toggle_schonmodus.sh


## 0.9.13
- Fix: main.py Indentation + manual_export drawtext escape + robust map-label.
- Barriere-Labels: AccessibleName/Description für zentrale Widgets/Buttons.


## 0.9.12
- Hilfe-Center im Tool: Tab 'Hilfe' mit Suche + HELP_CENTER.md.
- Laien-Quickstart + FAQ/Fehlerhilfe.


## 0.9.11
- Werkbank: Bild-Zuweisung für Stapel (1 Bild für alle / der Reihe nach / manuell via Zuweisungsliste).


## 0.9.10
- Werkbank-Export: Standbild+Audio direkt aus der Auswahl (Stapel möglich).
- Optional: Lauftext + Logo + Schwarz/Weiß (ohne Qualitätsverlust, Ton Safe).
- Script: app/manual_export.py (ffmpeg drawtext/overlay)


## 0.9.9
- Quarantäne-Tagesliste als UI-Tabelle im Tool (statt nur JSON öffnen).
- Aktionen: Neu (Ton Safe), Zurückstellen, Erledigt, Quarantäne-Ordner öffnen.


## 0.9.8
- Werkstatt-Aufräumen: Log-Rotation + Cache/Temp/Reports Cleanup (sicher, ohne Exports/Library anzufassen).
- Maintenance läuft automatisch beim Start und vor Automatik-Lauf.
- Maintenance Summary: portable_data/logs/maintenance_last.json


## 0.9.7
- Einstellungen-Editor im Tool: Pfade, Audio-Qualität, Dateinamen (alles deutsch, laienfest).
- Pfad-Test per Klick (schreibbar/sicher) + Standard wiederherstellen.
- Live-Vorschau Dateiname.


## 0.9.6
- Favoritenverwaltung im Werkzeugkasten: hinzufügen/entfernen, Stern, Tags, Suche, Tagfilter.
- Favoriten werden JSON-basiert gespeichert (user_data/favorites/favorites.json).


## 0.9.5
- Sortieren/Filtern überall: Suchfelder + Typfilter im Material und in der Auswahl.
- Letzte Nacht: Suchfelder für Quarantäne und Ausgaben.


## 0.9.4
- Thumbnails + Bildvorschau: Materialliste zeigt Mini-Vorschaubilder, Klick zeigt große Vorschau.
- Auswahlkorb zeigt Mini-Thumbnails für Bilder.
- Thumbnail-Cache in portable_data/cache/thumbs.


## 0.9.3
- Echt-Import: Drag&Drop + Dateien/Ordner holen im Material-Tab.
- Auswahlkorb editierbar: Umbenennen (Linux-sicher) + Entfernen aus Auswahl.
- Materialliste sortierbar (Datum/Name).


## 0.9.2
- Selftest komplett integriert (1 Erfolg + 1 Quarantäne) inkl. automatischer Dashboard-Aktualisierung.
- Automation Runner: CLI-Args für Settings/Rules (Overlays ohne Nutzer-Settings zu verändern).
- Bitrate-Validierung robust: fehlende Bitrate zählt als FAIL bei gesetztem Minimum.
- Selftest Runner + Script hinzugefügt.


## 0.9.1
- Entwicklerdoku im Tool (Tab + Datei DEVELOPER_MANUAL.md).
- Automatik-Runner verbessert: Bilder committen, Quarantäne-Jobs pro Tag schreiben.
- Quarantäne-Worker zum erneuten Erstellen (Ton Safe) + Abhaken-Logik.
- Dashboard 'Letzte Nacht' liest Reports/Quarantäne-Jobs und bietet Aktionen (Abspielen, Neu, Quelle ersetzen).


## 0.9.0
- Portable Grundgerüst (Werkstatt-UI, Auswahlkorb, Automatik-Grundlauf).
- Datensichere Pipeline: Zwischenablage → Temp → Validierung → Commit.
- Ton-Safe Vorlagen (YouTube HD, Shorts 9:16) + Tonprüfung nach Export.
- Quarantäne-Aufträge pro Tag + Abhaken-Logik.
- Werkstatt-Textpaket (deutsch, mild frech) JSON-basiert.
