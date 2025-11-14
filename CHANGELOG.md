# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

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

[1.0.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.4.0...v1.0.0
[0.4.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/feiglein74/BK1788-Python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/feiglein74/BK1788-Python/releases/tag/v0.1.0
