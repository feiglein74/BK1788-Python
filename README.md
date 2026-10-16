# BK1788-Python — control the B&K Precision 1788B power supply from Python

Python GUI and library to control and monitor the **B&K Precision 1788B** (32 V / 6 A) programmable
DC power supply via its **TTL serial interface** (IT-E131 adapter or a 5 V USB-TTL adapter).
Live graphs for voltage, current and power, setpoints, output and remote mode, auto-reconnect.

![License](https://img.shields.io/github/license/feiglein74/BK1788-Python)
![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/interface-TTL%20serial%20(5%20V)-555)
![Release](https://img.shields.io/github/v/release/feiglein74/BK1788-Python)

<!-- Screenshot folgt: docs/screenshot.png (GUI mit angeschlossenem Gerät) -->

## Quickstart

**Windows, no Python needed:** download `BK1788B-Steuerung-windows.zip` from
[Releases](https://github.com/feiglein74/BK1788-Python/releases), unzip, run `BK1788B-Steuerung.exe`.

**From source** (Windows, Linux, macOS):

```bash
git clone https://github.com/feiglein74/BK1788-Python.git
cd BK1788-Python
pip install -r requirements.txt
python gui_app.py
```

**As a library:**

```python
from bk1788b import BK1788B

psu = BK1788B(port='COM3', baudrate=4800)
if psu.connect():
    psu.set_remote_mode(True)      # required, otherwise set commands are rejected (0xB0)
    psu.set_voltage(12.0)
    psu.set_current(1.5)
    psu.set_output(True)
    print(psu.read_status())       # actual V/A, setpoints, CV/CC mode, temperature, fan
    psu.disconnect()
```

## Key facts

> Detailed documentation is in German (except the protocol reference, which is in English).

- **TTL, not RS-232.** The DB9 port of the 1788B uses 0–5 V levels. Never connect ±12 V RS-232
  directly. Wiring: adapter TX → pin 2, adapter RX ← pin 3, GND → pin 5 (straight-through).
- **Serial settings:** 4800 baud by default (9600/19200/38400 selectable under MENU > BAUDRATE), 8N1, no handshake.
- **Remote mode is mandatory** for set commands; without it the supply answers `0xB0` (unrecognized command).
  If a crash leaves the front panel locked, run `python unlock_netzteil.py COM3`.
- **Protocol / command set:** 26-byte frames, start byte `0xAA`, checksum = sum of bytes 0–24 mod 256,
  little-endian values in mV/mA. Full reference: [BK1788B_Protocol_Documentation.md](BK1788B_Protocol_Documentation.md)
  (English). Pitfalls found in practice (desync, buffer handling, timing): [KOMMUNIKATION_BESONDERHEITEN.md](KOMMUNIKATION_BESONDERHEITEN.md).
- **Repair note:** a 1788B stuck in constant-current (CC) mode with 0 V output after back-feeding from a
  large battery was caused by a shorted reverse-protection diode **1D24 (1N5408)**. Replacing it fixed the unit;
  calibration was not affected. Measurement plan: [REPARATUR_MESSPLAN.md](REPARATUR_MESSPLAN.md).
  The 1788B shares its schematic with the 1785B (mainboard is a rebadged ITECH IT6830 design).
- Manufacturer manual and schematic are copyrighted and **not** included; see below where to get them.

---

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

**Windows ohne Python:** `BK1788B-Steuerung-windows.zip` unter [Releases](https://github.com/feiglein74/BK1788-Python/releases) herunterladen, entpacken, `BK1788B-Steuerung.exe` starten.

**Aus dem Quellcode:**

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
├── unlock_netzteil.py                  # Remote-Modus abschalten (Frontpanel entsperren)
├── __version__.py                      # Versionsnummer
├── BK1788B.spec                        # PyInstaller-Build (Windows-EXE)
├── requirements.txt                    # Python-Abhängigkeiten
├── BK1788B_Protocol_Documentation.md   # Vollständige Protokolldokumentation (englisch)
├── KOMMUNIKATION_BESONDERHEITEN.md     # Fallstricke der seriellen Kommunikation
├── REPARATUR_MESSPLAN.md               # Mess-/Diagnoseplan „hängt in CC, 0 V“
├── CHANGELOG.md                        # Änderungshistorie
├── README.md                           # Diese Datei
└── CLAUDE.md                           # Entwickler-Dokumentation
```

## Hersteller-Dokumentation (nicht im Repo enthalten)

Das offizielle Instruction Manual und der Schaltplan sind **urheberrechtlich geschützt (© B&K Precision)** und werden hier **nicht mitgeliefert** (per `.gitignore` ausgeschlossen). Bezugsquellen:

| Dokument | Bezugsquelle |
|---|---|
| **Instruction Manual 1788B** | Offizielle B&K-Precision-Website → Produktseite 1788B → Downloads |
| **Schaltplan 1785B/1788** | EEVblog-Repair-Thread zum 1785B/1788 (von B&K an Kunden herausgegeben) |

Reparatur-/Messhinweise auf Basis des Schaltplans (eigene Analyse) stehen in [`REPARATUR_MESSPLAN.md`](REPARATUR_MESSPLAN.md).

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

[MIT](LICENSE). Das Projekt basiert auf Protokoll-Analyse und Field-Testing am BK1788B.
B&K Precision ist eine Marke der B&K Precision Corporation; dieses Projekt ist nicht mit dem Hersteller verbunden.

## Support

- **Protokoll-Dokumentation**: Siehe `BK1788B_Protocol_Documentation.md`
- **BK Precision Support**: https://www.bkprecision.com
- **Hardware Manual**: BK Precision 1788 Instruction Manual (November 3, 2010)

## Credits

Entwickelt basierend auf Protokoll-Analyse und Field-Testing mit Bus Pirate 6XL.

**Version**: siehe [CHANGELOG.md](CHANGELOG.md)
**Status**: Getestet und funktionsfähig
