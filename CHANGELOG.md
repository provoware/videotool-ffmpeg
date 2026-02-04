# CHANGELOG

## 1.0.53 - 2026-02-04
Verbessert: Logging bereinigt ungültige Meldungen und meldet Log-Fehler sichtbar, der Preflight setzt ungültige Themes sicher auf den Standard zurück (mit Debug-Hinweis), und die Start-Routine führt bei RUN_CHECKS vollständige Release-Checks aus.

## 1.0.52 - 2026-02-06
Verbessert: Favoriten-Logik in eigenen Controller ausgelagert (inkl. Fix, damit alle Einträge angezeigt werden), Einstellungen sind in einen Controller mit klarer Validierung umgezogen, und Quarantäne-Aktionen laufen nun in einem separaten Modul für bessere Wartbarkeit.

## 1.0.51 - 2026-02-05
Verbessert: Start-Routine prüft jetzt FFmpeg/ffprobe konsistent und bricht mit klaren Optionen ab, die Systemeinrichtung unterstützt mehrere Paketmanager mit verständlichem Fehlerbild, und die Must-Pass Suite überspringt fehlende FFmpeg/ffprobe sauber bzw. meldet fehlendes python3 klar.

## 1.0.50 - 2026-02-05
Verbessert: Preflight-Zeitstempel ist jetzt zeitzonen-sicher (keine Warnung), der Werkstatt-Check fängt leere/defekte JSON-Ausgaben ab und erklärt einfache Debug-Befehle, und Qualitäts-Checks geben klare Installationsbefehle für rg (ripgrep) aus.

## 1.0.49 - 2026-02-05
Verbessert: main.py startet die UI jetzt über klare App/Window/Runner-Klassen mit Validierung und Logging, damit Fehler und Exit-Codes nachvollziehbar bleiben.

## 1.0.48 - 2026-02-04
Verbessert: Quarantäne-Aktionen prüfen die Auswahl mit klarer Rückmeldung, der Quarantäne-Ordner wird mit Validierung geöffnet, und die Namensvorschau erklärt Vorlagen-Fehler in einfacher Sprache.

## 1.0.47 - 2026-02-03
Verbessert: Aktivitäts-Logging prüft Eingaben, Pfad-Öffnen meldet fehlende Ziele klar, und die letzte Report-Datei wird robuster ermittelt (stabilere Rückmeldungen in der Oberfläche).
