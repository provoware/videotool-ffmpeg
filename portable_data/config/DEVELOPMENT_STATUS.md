# Entwicklungsstand – Modultool Video-Werkstatt

- Version: 1.0.37
- Fortschritt: 61/61 = **100%**
- Nächster Schritt: **CI-Workflow (Continuous Integration = automatischer Build-Server) für die Must-Pass-Suite einrichten**

## ✅ Fertig
1. Portable Struktur
2. Klickstart venv
3. FFmpeg Setup sudo
4. Timer global
5. Textpaket/Deutsch
6. Themes (sehschwach)
7. Automatik Transaktion
8. Tonprüfung Ton Safe
9. Quarantäne pro Tag + Abhaken
10. Quarantäne-Worker
11. Dashboard Letzte Nacht
12. Entwicklerdoku
13. Hilfe-Center
14. Selftest
15. Werkbank Export (Text/Logo/SW)
16. Batch-Zuweisung Werkbank
17. Favoriten
18. Einstellungen-Editor
19. Maintenance/Cleanup
20. Must-Pass Suite
21. Schonmodus Threads
22. Preflight/Werkstatt-Check (neu)
23. Thumbnail-Regressionstest in Must-Pass Suite
24. Start-Routine: Abhängigkeiten prüfen und Nutzer-Feedback bündeln
25. Barrierefreiheit: Kontrast-Checks für alle Themes automatisieren
26. Qualitäts-Checks: Compile, Bash-Check, Marker-Scan, Must-Pass
27. Debug-Modus (Log-Level) + gezielte Fehlerberichte
28. Preflight: Watchfolder-Schreibrecht prüfen und melden
29. Maintenance: Settings-Ints sicher parsen und Warnungen im Summary loggen
30. Pfadlogik zentralisiert (paths = Speicherorte) für weniger Duplikate
31. Qualitäts-Checks: Formatprüfung mit ruff integriert
32. Maintenance: Dateifehler werden als Warnungen im Summary protokolliert
33. Preflight: fehlenden Watchfolder automatisch anlegen (Self-Repair)
34. Automatik: leere Dateinamen-Slugs mit sicherem Fallback absichern
35. Automatik: Lock-Datei mit Timeout und PID-Erkennung gegen parallele Läufe härten
36. Automatik: Download-Stabilität per Hash/MTime absichern
37. Subprozess-Schutz: Pfade/Dateien vor FFmpeg strikt validieren
38. Fehlerberichte: Report + GUI zeigen Abbrüche ohne SystemExit
39. Validierung: Ausgabe-Pfade prüfen Schreibrechte und verhindern Ordner-Zielpfade
40. Fehlerberichte: base_data_dir validieren und Fehler im Debug-Log erfassen
41. Preflight: Settings-JSON nur bei gültiger Dict-Struktur übernehmen
42. Release-Pakete automatisieren (ZIP, .deb, Must-Pass)
43. Zentrales Logging-Modul mit getrenntem User-Feedback
44. Konfigurationsvalidierung mit Schema- und Pfad-Checks
45. Werkbank-Export: FFmpeg-Fehler klar melden und Temp-Dateien sicher bereinigen
46. Preflight: settings_ok blockt ungültige Konfigurationen inkl. min_free_mb
47. Quarantäne-Worker: fehlendes ffmpeg/ffprobe wird klar gemeldet
48. Werkbank: fehlender Font meldet Hinweis statt still zu überspringen
49. Performance: Thread-Anzahl fällt dynamisch auf CPU-Kerne zurück (Eco halbiert)
50. Reports/Quarantäne-Listen: Schema-Normalisierung ergänzt Titel/Summary/Statusfelder
51. Plattform-Hinweise: Pfad-Öffnen unterstützt macOS/Windows, README ergänzt Start-Notizen
52. Automatik: Fallback-Bild wird vorab geprüft und fehlende Bilder landen in Quarantäne
53. Automatik: Ungültige Ausgabe-Pfade führen zu Quarantäne statt Abbruch
54. Selftest: Fehlende Testassets brechen mit klarer Meldung ab
55. main.py modularisieren (UI-Logik trennen, Wartbarkeit erhöhen)
56. Start-Routine: Bootstrap-Logik für Python-Abhängigkeiten zentralisiert
57. Start-Routine: optionaler FFmpeg-Autoinstall mit laienfreundlichem Hinweis
58. Qualitäts-Checks: Dev-Abhängigkeiten und Pflichtpakete über Bootstrap validiert
59. Preflight: Theme-Auswahl wird geprüft und meldet unbekannte Themes
60. UI/Start: Theme-Fallback & Preflight-Empfehlungen erweitert
61. Quarantäne-Tabelle: Inline-Bearbeitung mit Validierung und modularer Controller-Logik

## 🔧 Offen
- (keine)
