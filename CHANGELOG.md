# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [1.2.0] - 2026-10-16

### Hinzugefügt
- Auto-Reconnect: Verbindungsverlust nach 5 aufeinanderfolgenden Fehlern erkannt, automatische Wiederverbindung sobald der Port wieder verfügbar ist (Status-Label orange während Reconnect; manuelles Trennen stoppt den Reconnect)
- PyInstaller-Build (`BK1788B.spec`) und GitHub-Action, die bei Tags `v*` ein Windows-ZIP als Release baut
- `REPARATUR_MESSPLAN.md`: Mess-/Diagnoseplan für „hängt in CC, 0 V Ausgang“
- MIT-Lizenz
- Englischer README-Kopf (Quickstart, Key facts), GitHub-Pages-Konfiguration

### Behoben
- matplotlib xlim-Warnung bei einzelnem Datenpunkt

### Dokumentation
- Herstellerdokumente (PDF) per `.gitignore` aus dem Repo ausgeschlossen, Bezugsquellen im README

## [1.1.0] - 2025-11-19

### Hinzugefügt
- Threading-Lock (comm_lock) schützt alle seriellen Kommunikations-Operationen
- Force-Sync Mechanismus: GUI wird nach Set-Operationen mit Netzteil verifiziert
- Focus-Tracking mit 200ms Delay für Spinboxes (verhindert Überschreiben während Eingabe)
- Setting-Protection Flag während Set-Operationen
- Focus-Handler: _voltage_focus_in/out, _current_focus_in/out mit Timer-Management
- Automatische GUI-Rücksetzung bei fehlgeschlagenen Set-Operationen

### Geändert
- Alle Set-Operationen (_set_voltage, _set_current, _toggle_output, _toggle_remote) mit Lock geschützt
- Monitor-Thread read_status() mit Lock geschützt (verhindert Race Conditions)
- GUI-Update Logik respektiert Focus UND Setting-in-Progress
- Status-Verifikation nach jeder Set-Operation
- FocusOut Events mit 200ms Delay (gibt Button-Click Zeit zum Reagieren)
- Verbinden/Trennen/on_closing mit Lock-geschützter Kommunikation

### Behoben
- Race Conditions zwischen Monitor-Thread und Set-Operationen
- GUI-Werte wurden während Tippen/Pfeiltasten-Nutzung überschrieben
- FocusOut-Event vor Button-Click führte zu verlorenen Eingaben
- Inkonsistente GUI nach fehlgeschlagenen Set-Operationen
- Frontpanel-Änderungen wurden teilweise ignoriert

### Technisch
- Bidirektionale Synchronisation (GUI ↔ Netzteil) vollständig wasserdicht
- Thread-Safety durch Lock-Mechanismus garantiert
- Error-Handling mit finally-Blocks für garantiertes Flag-Zurücksetzen
- Intelligente GUI-Update Logik: Nicht überschreiben wenn Focus ODER Setting aktiv

## [1.0.0] - 2025-11-14

### Hinzugefügt
- Max. Spannung des Geräts wird aus Protokoll ausgelesen und in GUI angezeigt
- Lüfter-Geschwindigkeit mit Stufenanzeige (0=Aus, 1-4=Variable, 5=Maximum)
- Farbcodierung für Lüfter-Status (Grau=Aus, Grün=Läuft)

### Geändert
- Non-blocking Monitoring-Stop beim Beenden für schnelleres Shutdown
- Kürzerer Thread-Join Timeout (1s statt 2s)
- Try-Catch für alle Cleanup-Operationen bei Programmende

### Dokumentation
- CLAUDE.md aktualisiert mit max_voltage und detaillierten fan_speed Werten
- .gitignore erweitert um .claude/settings.local.json

## [0.4.0] - 2025-11-14

### Hinzugefügt
- Modus-abhängige Graphfärbung (CV=Blau, CC=Orange, Unreg=Grau)
- Separate Y-Achsen für Spannung (links) und Strom (rechts)
- Komma-Unterstützung für deutsche Tastatur in Eingabefeldern
- Enter-Taste für schnelle Wert-Übernahme in Spinboxes

### Geändert
- Spannungs-Graph wechselt Farbe je nach Betriebsmodus
- Optimierte Graph-Skalierung mit unabhängigen Y-Achsen
- Automatische Konvertierung Komma → Punkt bei Eingabe

## [0.3.0] - 2025-11-14

### Hinzugefügt
- Auto-Unlock beim Verbinden (Remote-Modus wird automatisch deaktiviert)
- Signal-Handler für Strg+C (SIGINT)
- unlock_netzteil.py Hilfsskript zum manuellen Entsperren
- Navigation-Toolbar für Graphen (Zoom, Pan, Save)
- Modus-Label mit Farbcodierung in GUI

### Geändert
- Sollwert-Synchronisation zwischen GUI und Netzteil beim Verbinden
- Remote-Modus AUS: GUI-Werte werden kontinuierlich vom Netzteil nachgeführt
- Remote-Modus wird beim Trennen/Schließen ausgeschaltet
- Graph-Beschriftungen mit festen Rändern (subplots_adjust)
- Auto-Skalierung pausiert bei manuellem Zoom/Pan

### Behoben
- Gesperrtes Frontpanel nach Programmabsturz
- Abgeschnittene Graph-Labels durch initiale Achsenlimits

## [0.2.0] - 2025-11-14

### Hinzugefügt
- COM-Port Dropdown mit automatischer Erkennung verfügbarer Ports
- Refresh-Button (🔄) zum Aktualisieren der Port-Liste
- Letzte Verbindungseinstellungen werden in gui_config.json gespeichert
- Automatisches Laden der Einstellungen beim Start

### Geändert
- Baudrate auf gültige BK1788B-Werte beschränkt (4800, 9600, 19200, 38400)
- Spannungs-/Strom-Anzeige mit gedimmter 3. Nachkommastelle (Messgenauigkeit)
- Spinboxes auf 2 Nachkommastellen (0.01V/A Schritte)
- Status-Labels direkt bei den zugehörigen Buttons
- Erfolgs-Popups entfernt (nur noch Fehler-Meldungen)
- Bessere Achsenbeschriftungen mit optimiertem Layout
- Schriftgrößen angepasst (fontsize=10 für Labels, labelsize=9 für Ticks)

### Entfernt
- Alle [DEBUG] Ausgaben aus bk1788b.py
- Unnötige Erfolgs-Popups

### Dokumentation
- BK1788B_Protocol_Documentation.md mit Kommunikations-Besonderheiten erweitert
- Troubleshooting-Sektion mit häufigsten Problemen und Lösungen

## [0.1.0] - 2025-11-14

### Hinzugefügt
- Vollständige RS-232/TTL Protokoll-Implementierung (26-Byte Pakete)
- BK1788B Klasse für Basis-Kommunikation (bk1788b.py)
- GUI mit tkinter für intuitive Bedienung (gui_app.py)
- Live-Graphen für Spannung, Strom und Leistung (matplotlib)
- Echtzeit-Monitoring mit 10 Hz Aktualisierungsrate
- Thread-sichere Kommunikation mit Lock-Mechanismus
- Automatische Remote-Modus Aktivierung bei Set-Kommandos
- Kommandos: Spannung/Strom setzen, Output ON/OFF, Remote ON/OFF, Status lesen
- Automatische Checksummen-Berechnung und -Validierung
- Little-Endian Encoding für Werte (mV für Spannung, mA für Strom)
- Status-Code Dekodierung (0x80=Success, 0xB0=Unrecognized, etc.)

### Dokumentation
- README.md mit Benutzer-Dokumentation
- BK1788B_Protocol_Documentation.md mit vollständiger Protokoll-Spezifikation
- CLAUDE.md für Entwickler
- requirements.txt mit Python-Abhängigkeiten

### Sicherheit
- TTL-Pegel Warnung (0-5V, NICHT RS-232 ±12V)

[1.1.0]: https://github.com/feiglein74/BK1788-Python/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.4.0...v1.0.0
[0.4.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/feiglein74/BK1788-Python/releases/tag/v0.1.0
