# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BK1788-Python** ist eine vollständige Python-Anwendung zur Steuerung und Überwachung des BK Precision 1788B Netzteils (0-32V, 0-6A) über RS-232/TTL.

Das Projekt umfasst:
- Vollständige Protokoll-Implementierung für BK1788B
- GUI-Anwendung mit tkinter
- Live-Graphen für Spannung, Strom und Leistung mit matplotlib
- Echtzeit-Monitoring (10 Hz)
- Thread-sichere Kommunikation

## Development Setup

### Initiales Setup
```bash
# Virtuelle Umgebung erstellen
python -m venv venv

# Aktivieren (Windows)
venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt
```

### Dependencies
- `pyserial>=3.5` - Serielle Kommunikation
- `matplotlib>=3.7.0` - Graphen und Visualisierung
- `numpy>=1.24.0` - Numerische Operationen

## Project Structure

```
BK1788-Python/
├── bk1788b.py                          # Basis-Kommunikationsmodul (BK1788B Klasse)
├── gui_app.py                          # Hauptanwendung mit GUI (PowerSupplyGUI Klasse)
├── requirements.txt                     # Python-Abhängigkeiten
├── BK1788B_Protocol_Documentation.md   # Vollständige RS-232/TTL Protokolldokumentation
├── README.md                            # Benutzer-Dokumentation
└── CLAUDE.md                            # Diese Datei
```

## Architecture

### bk1788b.py - Kommunikationsmodul
**Klasse**: `BK1788B`

**Kern-Funktionalität**:
- Implementiert 26-Byte Paket-Protokoll (Start-Marker 0xAA, Checksumme)
- Kommandos: Remote-Modus, Output ON/OFF, Spannung/Strom setzen, Status lesen
- Little-Endian Encoding für Werte (mV für Spannung, mA für Strom)
- Automatische Checksummen-Berechnung und -Validierung

**Wichtige Methoden**:
- `connect()` / `disconnect()` - Verbindungsmanagement
- `set_voltage(voltage)` - Spannung in Volt (0-32V)
- `set_current(current)` - Strom in Ampere (0-6A)
- `set_output(enable)` - Ausgang EIN/AUS
- `read_status()` - Gibt Dictionary mit allen Status-Informationen zurück

**Status-Dictionary**:
```python
{
    'actual_voltage': float,      # Aktuelle Spannung in V
    'actual_current': float,      # Aktueller Strom in A
    'voltage_setpoint': float,    # Spannungs-Sollwert
    'current_setpoint': float,    # Strom-Sollwert
    'output_on': bool,            # Ausgang aktiv
    'mode': str,                  # 'CV', 'CC', 'Unreg', 'Unknown'
    'remote_mode': bool,          # Remote-Steuerung aktiv
    'over_temp': bool,            # Übertemperatur-Schutz
    'fan_speed': int              # 0-5
}
```

### gui_app.py - GUI Anwendung
**Klasse**: `PowerSupplyGUI`

**Architektur**:
- **Hauptthread**: tkinter GUI, Event-Handling
- **Monitor-Thread**: Kontinuierliche Datenabfrage (10 Hz) über `_monitor_loop()`
- **Thread-Kommunikation**: `last_status` Dictionary als Shared State
- **GUI-Updates**: Via `_schedule_gui_update()` mit tkinter's `after()` (100ms Intervall)

**GUI-Komponenten**:
1. **Verbindungsbereich**: COM-Port und Baudrate-Auswahl
2. **Steuerung**: Spinboxes für Spannung/Strom, Buttons für Output/Remote
3. **Anzeige**: Große numerische Displays + Status-Labels
4. **Graphen**: Zwei matplotlib Subplots (Spannung/Strom + Leistung)

**Daten-Management**:
- `collections.deque` mit max. 500 Datenpunkten für Graphen
- Automatische Zeitachse (relative Zeit seit Start)
- Live-Update mit `canvas.draw_idle()`

## Common Commands

### Anwendung starten
```bash
python gui_app.py
```

### Basis-Modul testen
```bash
python bk1788b.py
```

### Dependencies aktualisieren
```bash
pip install -r requirements.txt --upgrade
```

## Hardware-Spezifikationen

**KRITISCH**: Das BK1788B verwendet **TTL-Pegel (0-5V)**, NICHT RS-232 (±12V)!

**Pinbelegung DB9**:
- Pin 2 (RX): Eingang zum Netzteil (TX vom Adapter)
- Pin 3 (TX): Ausgang vom Netzteil (RX am Adapter)
- Pin 5 (GND): Ground

**Kommunikationsparameter**:
- Baudrate: 4800 (Standard), 9600, 19200 oder 38400
- Format: 8N1 (8 Datenbits, No Parity, 1 Stopbit)
- Kein Hardware-Handshake

**Wichtig**: Baudrate am Netzteil prüfen (MENU > BAUDRATE) - muss mit Software übereinstimmen!

## Protocol Details

**Paket-Struktur** (26 Bytes):
```
Byte 0:      0xAA           (Start-Marker)
Byte 1:      Address        (Standard: 0x00)
Byte 2:      Command        (siehe Kommandos)
Bytes 3-24:  Data           (22 Bytes)
Byte 25:     Checksum       (sum(0:25) % 256)
```

**Kommando-Codes**:
- `0x20`: Remote-Modus setzen
- `0x21`: Output ON/OFF
- `0x23`: Spannung setzen (4-Byte LE in mV)
- `0x24`: Strom setzen (2-Byte LE in mA)
- `0x26`: Status lesen
- `0x12`: Status-Response (Erfolg: 0x80)

**Status-Byte Dekodierung** (Byte 9 der 0x26-Response):
- Bit 0: Output ON
- Bit 1: Over-Temperature
- Bit 2-3: Mode (01=CV, 10=CC, 11=Unreg)
- Bit 4-6: Fan Speed
- Bit 7: Remote Mode

## Development Notes

### Threading-Modell
- **Monitor-Thread**: Blockiert nicht die GUI, läuft mit `daemon=True`
- **Synchronisation**: Einfaches Flag `self.monitoring` zum Stoppen
- **Keine Locks nötig**: Thread schreibt nur, GUI liest nur aus `last_status`

### Error Handling
- Alle seriellen Operationen in try-except
- Checksummen-Validierung bei jedem Empfang
- Automatische Wiederverbindung nicht implementiert (User muss manuell neu verbinden)

### Grafik-Performance
- `draw_idle()` statt `draw()` - vermeidet unnötige Redraws
- Automatische Achsenskalierung
- Begrenzte Datenpunkte (500) verhindert Memory-Leak

### Typische Erweiterungen
- Datenlogging in CSV/Excel
- Automatische Sequenzen (z.B. Spannungs-Rampen)
- Presets speichern/laden
- Multi-Device Support (Adressierung 0x00-0xFE)

## Testing Checklist

Beim Testen/Debugging beachten:
- [ ] COM-Port korrekt? (Windows: Geräte-Manager)
- [ ] Baudrate identisch am Netzteil und in Software?
- [ ] TTL-Adapter auf 5V (nicht 3.3V)?
- [ ] Straight-through Verkabelung (nicht gekreuzt)?
- [ ] "LINK" Indikator erscheint am Display während Kommunikation?
- [ ] Checksummen-Fehler? → Elektrische Störungen, kürzere Kabel

## Sicherheit

- Immer Spannung/Strom vor Anschluss einer Last verifizieren
- Strombegrenzung zum Schutz empfindlicher Loads verwenden
- Bei Over-Temperature Warnung: Last reduzieren, Belüftung prüfen
