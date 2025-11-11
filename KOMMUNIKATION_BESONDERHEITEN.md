# BK1788B Kommunikation - Besonderheiten und Fallstricke

Dieses Dokument beschreibt die wichtigsten Besonderheiten, Fallstricke und Lösungen bei der Kommunikation mit dem BK Precision 1788B Netzteil, die während der Entwicklung entdeckt wurden.

## Inhaltsverzeichnis

1. [Remote-Modus Voraussetzung](#remote-modus-voraussetzung)
2. [Thread-Synchronisation](#thread-synchronisation)
3. [Paket-Desynchronisation](#paket-desynchronisation)
4. [Status-Code Dekodierung](#status-code-dekodierung)
5. [Buffer-Management](#buffer-management)
6. [Timing und Delays](#timing-und-delays)
7. [Checksummen-Validierung](#checksummen-validierung)
8. [Best Practices](#best-practices)

---

## Remote-Modus Voraussetzung

### Problem

**Set-Kommandos (0x23 Spannung, 0x24 Strom) werden mit Status-Code 0xB0 (Unrecognized Command) abgelehnt, wenn das Netzteil nicht im Remote-Modus ist.**

```
Ohne Remote-Modus:
Sende: AA 00 23 88 13 00 00 ... (Set Voltage 5V)
Empfange: AA 00 12 B0 ...       (Status: 0xB0 = Unrecognized)
```

### Ursache

Das BK1788B unterscheidet zwischen zwei Betriebsmodi:
- **Front-Panel Modus**: Nur Frontpanel-Bedienung erlaubt, PC-Kommandos werden ignoriert/abgelehnt
- **Remote-Modus**: PC-Steuerung aktiv, Set-Kommandos werden akzeptiert

Im Front-Panel Modus können Sie **nur lesen** (Status 0x26), aber **nicht schreiben**.

### Lösung

**Immer vor Set-Kommandos prüfen ob Remote-Modus aktiv ist:**

```python
def set_voltage(self, voltage: float) -> bool:
    # Zuerst Remote-Modus prüfen und ggf. aktivieren
    status = self.read_status()
    if status and not status['remote_mode']:
        print("Remote-Modus nicht aktiv - aktiviere jetzt...")
        if not self.set_remote_mode(True):
            return False

    # Jetzt Spannung setzen
    # ...
```

### Erkennung am Gerät

- **Display zeigt "Rmt"**: Remote-Modus ist aktiv ✓
- **Kein "Rmt" im Display**: Front-Panel Modus, Set-Kommandos werden abgelehnt ✗

### Wichtig

Der Remote-Modus wird **nicht automatisch** bei Verbindungsaufbau aktiviert! Sie müssen explizit das 0x20-Kommando senden.

---

## Thread-Synchronisation

### Problem

**Bei gleichzeitigem Monitoring (kontinuierliches Lesen) und Set-Kommandos kommt es zu Race Conditions und falschen Responses.**

```
Thread 1 (Monitor):  Sende 0x26 (Read Status) ──┐
Thread 2 (GUI):      Sende 0x23 (Set Voltage) ───┤
                                                  ├─> Pakete überschneiden sich!
Thread 1:            Empfange Response von 0x23  ─┤
Thread 2:            Empfange Response von 0x26 ──┘
```

### Symptome

- Set-Kommandos schlagen fehl obwohl sie korrekt sind
- Response besteht nur aus Nullen (0x00)
- Checksummen-Fehler durch verschobene Pakete
- Unvorhersagbares Verhalten

### Ursache

Serielle Kommunikation ist **nicht thread-sicher**. Wenn zwei Threads gleichzeitig senden:
1. Pakete können sich vermischen
2. Responses kommen beim falschen Thread an
3. Buffer läuft über oder wird inkonsistent

### Lösung

**Threading-Lock für alle seriellen Operationen:**

```python
import threading

class BK1788B:
    def __init__(self, ...):
        self.comm_lock = threading.Lock()

    def _send_command(self, command, data):
        # LOCK: Nur ein Thread darf gleichzeitig kommunizieren
        with self.comm_lock:
            self.serial.reset_input_buffer()  # Buffer leeren
            self.serial.write(packet)
            response = self.serial.read(26)
            return response
```

**Resultat:**
- Monitoring-Thread wartet, wenn GUI-Thread sendet
- Keine Race Conditions mehr
- Jedes Kommando bekommt die richtige Response

### Performance-Hinweis

Der Lock führt zu kurzen Wartezeiten (ca. 50-100ms bei 4800 Baud), aber das ist akzeptabel für:
- Monitoring mit 10 Hz (alle 100ms)
- Gelegentliche Set-Kommandos vom User

---

## Paket-Desynchronisation

### Problem

**Empfangene Pakete sind verschoben - das Start-Byte 0xAA ist nicht an Position 0:**

```
Erwartet:   AA 00 26 3C 00 D6 2E 00 00 05 96 00 E8 80 00 00 ...
Empfangen:  00 F0 09 00 01 00 00 00 00 22 AA 00 26 3C 00 D6 ...
                                       ^^^^^^^^^^^ Hier ist das echte Paket!
```

### Ursache

1. **Buffer enthält noch alte Daten** von vorherigen Kommandos
2. **Pakete überlappen** durch fehlende Synchronisation
3. **Timing-Probleme** - Response kommt bevor Read aufgerufen wird

### Symptome

- Checksummen-Fehler
- Start-Marker 0xAA nicht an Position 0
- Response beginnt mitten im empfangenen Buffer

### Lösung

**Input-Buffer vor jedem Senden leeren:**

```python
def _send_command(self, command, data):
    with self.comm_lock:
        # WICHTIG: Buffer leeren BEVOR gesendet wird
        self.serial.reset_input_buffer()

        packet = self._create_packet(command, data)
        self.serial.write(packet)

        # Kurze Pause für das Netzteil
        time.sleep(0.05)  # 50ms

        response = self.serial.read(26)
        return response
```

**Zusätzliche Validierung:**

```python
# Prüfen ob Response nur Nullen enthält
if all(b == 0 for b in response):
    print("FEHLER: Response besteht nur aus Nullen!")
    return None

# Start-Marker prüfen
if response[0] != 0xAA:
    print(f"FEHLER: Start-Marker ist 0x{response[0]:02X} statt 0xAA!")
    return None
```

---

## Status-Code Dekodierung

### Übersicht Status-Response (0x12)

Jedes Set-Kommando (außer 0x26 Read) antwortet mit einem 0x12 Status-Paket:

```
Byte 0:  0xAA           (Start-Marker)
Byte 1:  0x00           (Adresse)
Byte 2:  0x12           (Status-Response)
Byte 3:  Status-Code    (Siehe unten)
Byte 4-24: 0x00         (Reserviert)
Byte 25: Checksum
```

### Status-Codes

| Code | Name | Bedeutung | Lösung |
|------|------|-----------|--------|
| `0x80` | Success | Kommando erfolgreich ausgeführt | ✓ Alles OK |
| `0x90` | Checksum Error | Checksumme im gesendeten Paket falsch | Paket neu senden |
| `0xA0` | Parameter Error | Wert außerhalb gültiger Range | Wert prüfen (z.B. >32V) |
| `0xB0` | Unrecognized Command | Kommando nicht erkannt oder nicht erlaubt | **Remote-Modus aktivieren!** |
| `0xC0` | Invalid Command | Kommando-Byte ungültig | Protokoll prüfen |

### Wichtigste Fehlerquelle: 0xB0

**0xB0 wird gesendet wenn:**
1. Remote-Modus nicht aktiv (häufigster Fall!)
2. Kommando-Byte wirklich unbekannt
3. Gerät in einem Modus wo Kommando nicht erlaubt ist

**Erste Maßnahme bei 0xB0:**
```python
if response[3] == 0xB0:
    print("Unrecognized Command - prüfe Remote-Modus!")
    status = self.read_status()
    if not status['remote_mode']:
        self.set_remote_mode(True)
```

---

## Buffer-Management

### Problem mit kontinuierlichem Monitoring

Bei 10 Hz Monitoring-Rate (alle 100ms ein Status-Read) kann sich der Input-Buffer füllen:

```
T=0ms:    Sende 0x26, Empfange 26 Bytes
T=100ms:  Sende 0x26, Empfange 26 Bytes
T=200ms:  Sende 0x26, Empfange 26 Bytes
...
```

Wenn ein Read zu spät kommt, sammeln sich Pakete im Buffer → Desynchronisation

### Lösung

**1. Buffer vor jedem Kommando leeren:**
```python
self.serial.reset_input_buffer()
```

**2. Timeout korrekt setzen:**
```python
self.serial = serial.Serial(
    port=port,
    baudrate=4800,
    timeout=1.0  # 1 Sekunde sollte ausreichen für 26 Bytes @ 4800 Baud
)
```

**3. Nicht zu schnell pollen:**
```python
# 10 Hz ist OK (100ms Pause)
time.sleep(0.1)

# 100 Hz ist zu schnell! (10ms - nicht genug Zeit für Response)
# time.sleep(0.01)  # NICHT tun!
```

### Berechnung Minimum-Pause

Bei 4800 Baud, 8N1:
- 1 Byte = 10 Bits (1 Start + 8 Data + 1 Stop)
- 4800 Baud = 480 Bytes/Sekunde
- 26 Bytes = 26 / 480 = **54ms Übertragungszeit**

**Minimum Pause zwischen Kommandos:** ca. 60-100ms

---

## Timing und Delays

### Notwendige Delays

**1. Nach dem Senden, vor dem Empfangen:**
```python
self.serial.write(packet)
time.sleep(0.05)  # 50ms - gibt dem Netzteil Zeit zu antworten
response = self.serial.read(26)
```

**Ohne Delay:** Response ist noch nicht komplett im Buffer → Timeout oder unvollständiges Paket

**2. Nach Connect:**
```python
self.serial = serial.Serial(...)
time.sleep(0.1)  # 100ms - Serial-Port stabilisieren
self.serial.reset_input_buffer()
```

**3. Zwischen Kommandos (Monitoring):**
```python
while monitoring:
    status = self.read_status()
    time.sleep(0.1)  # 100ms = 10 Hz Rate
```

### Baudrate-Abhängigkeit

| Baudrate | Min. Delay | Empfohlen |
|----------|------------|-----------|
| 4800 | 50ms | 100ms |
| 9600 | 30ms | 50ms |
| 19200 | 15ms | 30ms |
| 38400 | 10ms | 20ms |

**Höhere Baudrate = schnellere Kommunikation = kürzere Delays möglich**

---

## Checksummen-Validierung

### Berechnung

```python
# Checksumme = Summe aller Bytes 0-24, Modulo 256
checksum = sum(packet[0:25]) % 256
packet[25] = checksum
```

### Beispiel

```
Paket: AA 00 26 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ??

Berechnung:
0xAA + 0x00 + 0x26 + (22 × 0x00) = 0xD0

Checksumme: 0xD0
```

### Wichtig

**Immer Checksumme prüfen beim Empfangen:**

```python
calculated = sum(response[0:25]) % 256
received = response[25]

if calculated != received:
    print(f"Checksummen-Fehler! Erwartet: {calculated:02X}, Erhalten: {received:02X}")
    return None  # Paket verwerfen
```

**Häufige Fehlerquellen:**
- Elektrische Störungen (schlechte Verkabelung)
- Baudrate-Mismatch
- TTL-Pegel nicht korrekt (3.3V statt 5V)
- Zu lange/ungeschirmte Kabel

---

## Best Practices

### 1. Verbindungsaufbau

```python
psu = BK1788B(port='COM3', baudrate=4800)

if psu.connect():
    # Erst Status lesen (funktioniert immer)
    status = psu.read_status()
    print(f"Spannung: {status['actual_voltage']}V")

    # Dann Remote-Modus aktivieren (für Set-Kommandos)
    psu.set_remote_mode(True)

    # Jetzt können Set-Kommandos verwendet werden
    psu.set_voltage(12.0)
    psu.set_output(True)
```

### 2. Fehlerbehandlung

```python
def set_voltage_safe(psu, voltage):
    """Sicheres Setzen der Spannung mit Retry"""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            if psu.set_voltage(voltage):
                # Verifizieren durch Status-Read
                time.sleep(0.1)
                status = psu.read_status()
                if abs(status['voltage_setpoint'] - voltage) < 0.01:
                    return True
                else:
                    print(f"Sollwert stimmt nicht: {status['voltage_setpoint']}V")

        except Exception as e:
            print(f"Versuch {attempt+1} fehlgeschlagen: {e}")

        time.sleep(0.5)  # Pause vor Retry

    return False
```

### 3. Monitoring Pattern

```python
class SafeMonitor:
    def __init__(self, psu):
        self.psu = psu
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _loop(self):
        consecutive_errors = 0

        while self.running:
            try:
                status = self.psu.read_status()
                if status:
                    self.on_status_update(status)
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    if consecutive_errors > 10:
                        print("Zu viele Fehler - stoppe Monitoring")
                        break

            except Exception as e:
                print(f"Monitor-Fehler: {e}")
                consecutive_errors += 1

            time.sleep(0.1)  # 10 Hz
```

### 4. Debug-Ausgaben

**Während Entwicklung:**
```python
print(f"[DEBUG] Sende: {' '.join(f'{b:02X}' for b in packet)}")
print(f"[DEBUG] Empfange: {' '.join(f'{b:02X}' for b in response)}")
```

**In Production:**
```python
# Debug-Ausgaben entfernen oder über Flag steuern
if DEBUG:
    print(f"[DEBUG] ...")
```

### 5. Hardware-Checks

**Vor jeder Session prüfen:**

- [ ] "LINK" erscheint im Display bei Kommunikation?
- [ ] Baudrate am Gerät korrekt eingestellt? (MENU > BAUDRATE)
- [ ] TTL-Adapter auf 5V (nicht 3.3V)?
- [ ] Verkabelung: TX→Pin2, RX←Pin3, GND→Pin5?
- [ ] Keine RS-232-Pegel (±12V) verwendet?

---

## Häufigste Probleme und Lösungen

### Problem: "Keine Response" oder "Nur Nullen empfangen"

**Ursachen:**
1. Baudrate-Mismatch → Gerät prüfen
2. Falsche Pinbelegung → TX/RX vertauscht?
3. TTL-Pegel falsch → 5V statt 3.3V?
4. COM-Port falsch → Geräte-Manager prüfen

**Lösung:** Hardware-Checks durchführen

---

### Problem: "Checksummen-Fehler"

**Ursachen:**
1. Elektrische Störungen → Kürzere/geschirmte Kabel
2. Baudrate zu hoch → Auf 4800 reduzieren
3. Schlechte Verbindung → Kontakte prüfen

**Lösung:** Hardware verbessern, niedrigere Baudrate

---

### Problem: "Status 0xB0 (Unrecognized)"

**Ursache:**
Remote-Modus nicht aktiv

**Lösung:**
```python
psu.set_remote_mode(True)
```

---

### Problem: "Set-Kommandos funktionieren sporadisch"

**Ursache:**
Thread-Race-Condition zwischen Monitoring und Set-Kommandos

**Lösung:**
Threading-Lock implementieren (siehe oben)

---

## Zusammenfassung

Die wichtigsten Punkte für zuverlässige Kommunikation:

1. ✅ **Remote-Modus aktivieren** vor Set-Kommandos
2. ✅ **Threading-Lock** für serielle Kommunikation
3. ✅ **Buffer leeren** vor jedem Senden
4. ✅ **Delays einhalten** (50-100ms nach Senden)
5. ✅ **Checksummen validieren** bei Empfang
6. ✅ **Status-Codes auswerten** und behandeln
7. ✅ **Hardware korrekt** (5V TTL, richtige Baudrate)
8. ✅ **Nicht zu schnell pollen** (max. 10 Hz bei 4800 Baud)

---

## Versions-Historie

**Version 1.0** - 2025-11-11
- Initiale Dokumentation basierend auf Field-Testing
- Alle bekannten Probleme und Lösungen dokumentiert

---

**Autor:** Entwickelt durch praktische Tests mit BK Precision 1788B und Bus Pirate 6XL / USB-TTL Adapter
**Hardware getestet:** BK Precision 1788B (32V/6A Modell)
**Status:** Verifiziert und in Produktion
