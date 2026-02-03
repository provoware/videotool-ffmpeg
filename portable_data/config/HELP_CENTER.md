# Hilfe-Center – Modultool Video-Werkstatt

Stand: 2026-02-03T00:30:20Z

## Schnellstart (60 Sekunden)
1. **Material holen**: Zieh Audio + Bild in den Material-Tab oder klick **Dateien holen**.
2. **Auswahl setzen**: Checkboxen anklicken. Oben in der Schaltzentrale siehst du **Deine Auswahl**.
3. **Werkbank**: Stell Vorlage ein (**YouTube HD Ton Safe** oder **Shorts Ton Safe**).
4. Optional:
   - Lauftext aktivieren + Text eintragen
   - Logo aktivieren + Datei wählen
   - Schwarz/Weiß an/aus
5. **Ausgabe bauen** klicken.
6. Fertig: **Ausgaben öffnen**.

## Automatik (22:00 oder andere Uhrzeit)
- In **Einstellungen** kannst du Pfade und Qualität prüfen.
- In **Automatik**: Zeitplan einrichten.
- Empfehlung: FFmpeg tagsüber einrichten, nachts Ruhe.

## Quarantäne (Problemfälle)
- Wenn etwas nicht passt: Es wird nicht weggeschmissen.
- Du bekommst einen Quarantäne-Auftrag (pro Tag).
- Im Tab **Quarantäne-Aufträge (heute)** kannst du:
  - Neu (Ton Safe)
  - Zurückstellen
  - Erledigt

## Häufige Probleme (und direkte Lösungen)
### „Kein FFmpeg“
- Lösung: **Systemeinrichtung (FFmpeg)** anklicken (sudo).
### „Ton klingt schlecht“
- Lösung: Nutze **Ton Safe**. Das Tool prüft Bitrate + Samplerate und blockt Müll.
### „Datei fehlt“
- Lösung: Datei neu wählen oder im Favoriten/Material neu hinzufügen.
### „Automatik macht nix“
- Lösung: Zeitplan einrichten, Watchfolder prüfen, Selftest laufen lassen.

## Werkstatt-Begriffe (damit’s nicht verwirrt)
- **Ausgabe** = fertiges Video
- **Zwischenablage** = staging (datensicher)
- **Quarantäne** = Problemfälle, nichts verloren
- **Werkzeugkasten** = Favoriten (Logos/Bilder)


## Werkstatt-Check (Preflight)
Wenn oben ein Warnschild steht: FFmpeg/Pfade/Speicher prüfen.
Knopf: "Jetzt einrichten (FFmpeg)" erledigt den Rest.

## Edgecases (Stabilitätsregeln)
- Wenn Export-Ordner nicht schreibbar ist, nutzt das Tool automatisch den sicheren Standard-Ordner.
- Wenn keine Schrift gefunden wird, wird Lauftext deaktiviert (damit nichts crasht).
- Wenn Logo fehlt, wird Logo übersprungen.
