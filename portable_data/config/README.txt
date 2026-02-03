MODULTOOL – VIDEO-WERKSTATT (PORTABLE)
README.txt

Start:
1) Ordner entpacken
2) tools/start.sh ausführen (erstellt venv + startet GUI)
3) Wenn FFmpeg fehlt: im Tool 'Systemeinrichtung' anklicken (sudo).

Ordner (portable_data):
- user_data/exports/           fertige Ausgaben
- user_data/library/audio/     benutzte Audios
- user_data/library/images/    benutzte Bilder
- user_data/quarantine/        Problemfälle
- user_data/quarantine_jobs/   Quarantäne-Aufträge pro Tag (abgehakt möglich)
- user_data/reports/           Arbeitsberichte
- user_data/staging/           Zwischenablage (datensicher)
- user_data/trash/             Papierkorb (erst nach Validierung)
- logs/                        Werkstatt-Protokoll
- cache/                       Thumbnails + Temp

Automatik (global, variierbar):
- config/automation_rules.json: start_time setzen (Default 22:00)
- tools/install_timer.sh: Zeitplan einrichten

Tonqualität:
- Vorlagen 'Ton Safe' erzwingen AAC 48kHz, 320k.
- Nach Export wird geprüft. Unter Minimum → kein Commit, Quarantäne-Auftrag.

Ende.
