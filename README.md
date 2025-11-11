# BK Precision 1788B - Python Steuerung mit GUI

Vollständige Python-Anwendung zur Steuerung und Überwachung des BK Precision 1788B Netzteils (0-32V, 0-6A) über RS-232/TTL.

## Features

- 🔌 **Vollständige Steuerung** über RS-232/TTL-Schnittstelle
- 📊 **Live-Graphen** für Spannung, Strom und Leistung
- 🖥️ **Intuitive GUI** mit tkinter
- 📈 **Echtzeit-Monitoring** mit 10 Hz Aktualisierungsrate
- ⚡ **Schnelle Sollwert-Änderung** für Spannung und Strom
- 🔄 **Remote-Modus** Steuerung
- 🛡️ **Sicherheitsanzeigen** (Übertemperatur, Betriebsmodus)

## Hardware-Anforderungen

⚠️ **WICHTIG**: Das BK1788B verwendet **TTL-Pegel (0-5V)**, NICHT RS-232 (±12V)!

### Empfohlene Adapter
- **Original**: BK Precision IT-E131 (RS-232 zu TTL mit galvanischer Trennung)
- **Alternative**: USB-zu-TTL Adapter (FTDI FT232RL oder ähnlich) auf 5V eingestellt

### Pinbelegung DB9
```
USB-TTL Adapter          BK 1788B (DB9)
-----------------        --------------
TX (MOSI)       ──────>  Pin 2 (RX)
RX (MISO)       <──────  Pin 3 (TX)
GND             ──────   Pin 5 (GND)
```

### Kommunikationsparameter
- **Baudrate**: 4800 (Standard), 9600, 19200 oder 38400
- **Datenbits**: 8
- **Parität**: None
- **Stopbits**: 1
- **Format**: 8N1
- **Handshake**: Keine

⚠️ **Baudrate am Netzteil prüfen**: MENU > BAUDRATE

## Installation

### 1. Repository klonen oder Dateien herunterladen
```bash
cd BK1788-Python
```

### 2. Virtuelle Umgebung erstellen (empfohlen)
```bash
python -m venv venv
```

### 3. Virtuelle Umgebung aktivieren

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

## Verwendung

### GUI-Anwendung starten
```bash
python gui_app.py
```

### Basis-Modul (nur Kommunikation)
```python
from bk1788b import BK1788B

# Netzteil initialisieren
psu = BK1788B(port='COM3', baudrate=4800)

# Verbinden
if psu.connect():
    # Remote-Modus aktivieren
    psu.set_remote_mode(True)

    # Spannung setzen (12.5V)
    psu.set_voltage(12.5)

    # Strombegrenzung setzen (1.5A)
    psu.set_current(1.5)

    # Ausgang einschalten
    psu.set_output(True)

    # Status lesen
    status = psu.read_status()
    print(f"Spannung: {status['actual_voltage']:.3f}V")
    print(f"Strom: {status['actual_current']:.3f}A")
    print(f"Modus: {status['mode']}")

    # Ausgang ausschalten
    psu.set_output(False)

    # Trennen
    psu.disconnect()
```

## GUI-Bedienung

### Verbindungsbereich
1. **COM-Port** eingeben (z.B. `COM3`)
2. **Baudrate** wählen (Standard: 4800)
3. **Verbinden** klicken

### Steuerung
- **Spannung setzen**: Wert eingeben (0-32V) und "Setzen" klicken
- **Strom setzen**: Wert eingeben (0-6A) und "Setzen" klicken
- **Ausgang EIN/AUS**: Button zum Umschalten des Ausgangs
- **Remote-Modus**: Button zum Aktivieren/Deaktivieren der PC-Steuerung

### Anzeige
- **Große Displays**: Aktuelle Spannung, Strom und Leistung
- **Status-Informationen**:
  - Betriebsmodus (CV = Constant Voltage, CC = Constant Current)
  - Ausgangsstatus (EIN/AUS)
  - Remote-Modus Status
  - Übertemperatur-Warnung

### Live-Graphen
- **Oberer Graph**: Spannung (blau) und Strom (rot) über Zeit
- **Unterer Graph**: Leistung (grün) über Zeit
- Automatische Skalierung und Zeitachse
- Speichert bis zu 500 Datenpunkte

## Dateistruktur

```
BK1788-Python/
├── bk1788b.py                          # Basis-Kommunikationsmodul
├── gui_app.py                          # Hauptanwendung mit GUI
├── requirements.txt                     # Python-Abhängigkeiten
├── BK1788B_Protocol_Documentation.md   # Vollständige Protokolldokumentation
├── README.md                            # Diese Datei
└── CLAUDE.md                            # Entwickler-Dokumentation
```

## Technische Details

### Protokoll
- **Paketgröße**: Immer 26 Bytes (Kommando und Antwort)
- **Format**: `[0xAA][Adresse][Kommando][Daten (22 Bytes)][Checksumme]`
- **Checksumme**: Summe Bytes 0-24, Modulo 256

### Wichtige Kommandos
- `0x20`: Remote-Modus setzen
- `0x21`: Ausgang EIN/AUS
- `0x23`: Spannung setzen (in mV, Little-Endian)
- `0x24`: Strom setzen (in mA, Little-Endian)
- `0x26`: Status lesen

### Monitoring
- **Update-Rate**: 10 Hz (alle 100ms)
- **Separate Threads**: Kommunikation läuft in eigenem Thread
- **Thread-sicher**: GUI-Updates über Tkinter's `after()`-Mechanismus

## Fehlerbehebung

### Problem: Keine Verbindung
**Lösung**:
- COM-Port prüfen (Windows: Geräte-Manager)
- Baudrate am Netzteil prüfen (MENU > BAUDRATE)
- TTL-Adapter auf 5V einstellen (nicht 3.3V)
- Kabel-Pinbelegung prüfen (straight-through, nicht gekreuzt)

### Problem: "LINK" erscheint nicht am Display
**Lösung**:
- Baudrate-Mismatch: Beide Seiten müssen identisch sein
- Pinbelegung prüfen: TX→Pin2, RX←Pin3, GND→Pin5
- Spannung prüfen: Muss 5V TTL sein

### Problem: Checksummen-Fehler
**Lösung**:
- Elektrische Störungen: Kürzere/abgeschirmte Kabel verwenden
- Baudrate zu hoch: Auf 4800 reduzieren
- Grounding prüfen

## Sicherheitshinweise

⚠️ **Vor Verwendung beachten:**
- Immer Spannung/Strom vor Anschluss einer Last prüfen
- Strombegrenzung zum Schutz empfindlicher Lasten verwenden
- Bei Übertemperatur-Warnung: Belüftung prüfen, Last reduzieren
- Niemals RS-232-Pegel (±12V) direkt am DB9 verwenden!

## Lizenz

Dieses Projekt basiert auf Reverse Engineering und Dokumentation des BK1788B Protokolls.
Für den persönlichen und kommerziellen Gebrauch frei verfügbar.

## Support

- **Protokoll-Dokumentation**: Siehe `BK1788B_Protocol_Documentation.md`
- **BK Precision Support**: https://bkprecision.desk.com
- **Hardware Manual**: BK Precision 1788 Instruction Manual (November 3, 2010)

## Credits

Entwickelt basierend auf Protokoll-Analyse und Field-Testing mit Bus Pirate 6XL.

**Version**: 1.0
**Datum**: 2025-11-11
**Status**: Getestet und funktionsfähig
