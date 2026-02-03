# CHANGELOG

## 1.0.10
- Themes: Hint/Muted-Farben zentral in themes.json, Kontrast-Check erweitert.


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
