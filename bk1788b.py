"""
BK Precision 1788B Netzteil - RS-232/TTL Kommunikationsmodul
Unterstützt vollständige Steuerung und Überwachung des Netzteils
"""

import serial
import time
import threading
from typing import Dict, Optional, Tuple


class BK1788B:
    """
    Klasse zur Kommunikation mit dem BK Precision 1788B Netzteil

    Protokoll: 26-Byte Pakete über RS-232/TTL
    Standard: 4800 Baud, 8N1, keine Handshakes
    """

    # Kommando-Codes
    CMD_SET_REMOTE = 0x20
    CMD_SET_OUTPUT = 0x21
    CMD_SET_VOLTAGE = 0x23
    CMD_SET_CURRENT = 0x24
    CMD_READ_STATUS = 0x26
    CMD_STATUS_RESPONSE = 0x12

    # Status-Codes
    STATUS_SUCCESS = 0x80
    STATUS_CHECKSUM_ERROR = 0x90
    STATUS_PARAM_ERROR = 0xA0
    STATUS_UNKNOWN_CMD = 0xB0
    STATUS_INVALID_CMD = 0xC0

    # Betriebsmodi
    MODE_UNKNOWN = 0
    MODE_CV = 1  # Constant Voltage
    MODE_CC = 2  # Constant Current
    MODE_UNREG = 3

    def __init__(self, port: str, baudrate: int = 4800, address: int = 0x00, timeout: float = 1.0):
        """
        Initialisiert die Verbindung zum Netzteil

        Args:
            port: COM-Port (z.B. 'COM3')
            baudrate: Baudrate (4800, 9600, 19200, 38400)
            address: Geräteadresse (Standard: 0x00)
            timeout: Timeout für Antworten in Sekunden
        """
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None
        self.comm_lock = threading.Lock()  # Lock für Thread-sichere Kommunikation

    def connect(self) -> bool:
        """
        Öffnet die serielle Verbindung

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            # Kurze Pause nach dem Öffnen
            time.sleep(0.1)
            # Buffer leeren
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            return True
        except Exception as e:
            print(f"Fehler beim Öffnen von {self.port}: {e}")
            return False

    def disconnect(self):
        """Schließt die serielle Verbindung"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.serial = None

    def is_connected(self) -> bool:
        """Prüft ob die Verbindung aktiv ist"""
        return self.serial is not None and self.serial.is_open

    def _create_packet(self, command: int, data: list) -> bytearray:
        """
        Erstellt ein 26-Byte Kommando-Paket

        Args:
            command: Kommando-Byte
            data: Datenbytes (max. 22 Bytes)

        Returns:
            Komplettes 26-Byte Paket mit Checksumme
        """
        packet = bytearray(26)
        packet[0] = 0xAA  # Start-Marker
        packet[1] = self.address
        packet[2] = command

        # Daten kopieren (max. 22 Bytes)
        for i, byte in enumerate(data[:22]):
            packet[3 + i] = byte

        # Checksumme berechnen (Summe Bytes 0-24, Modulo 256)
        packet[25] = sum(packet[0:25]) % 256

        return packet

    def _send_command(self, command: int, data: list) -> Optional[bytearray]:
        """
        Sendet ein Kommando und wartet auf Antwort
        Thread-sicher durch Lock

        Args:
            command: Kommando-Byte
            data: Datenbytes

        Returns:
            Empfangenes 26-Byte Paket oder None bei Fehler
        """
        if not self.is_connected():
            raise ConnectionError("Nicht mit dem Netzteil verbunden")

        # LOCK: Nur ein Thread darf gleichzeitig kommunizieren
        with self.comm_lock:
            # Buffer vor dem Senden leeren (alte Daten entfernen)
            self.serial.reset_input_buffer()

            # Paket erstellen und senden
            packet = self._create_packet(command, data)
            self.serial.write(packet)

            # Kurze Pause für das Netzteil
            time.sleep(0.05)

            # Auf Antwort warten (immer 26 Bytes)
            response = self.serial.read(26)

            if len(response) != 26:
                return None

            # Prüfen ob Response nur Nullen enthält
            if all(b == 0 for b in response):
                return None

            # Checksumme prüfen
            calculated_checksum = sum(response[0:25]) % 256
            if response[25] != calculated_checksum:
                return None

            return bytearray(response)

    def set_remote_mode(self, enable: bool = True) -> bool:
        """
        Aktiviert/Deaktiviert Remote-Steuerung

        Args:
            enable: True für Remote-Modus, False für Frontpanel

        Returns:
            True bei Erfolg
        """
        data = [0x01 if enable else 0x00] + [0x00] * 21
        response = self._send_command(self.CMD_SET_REMOTE, data)

        if response and response[2] == self.CMD_STATUS_RESPONSE:
            return response[3] == self.STATUS_SUCCESS

        return False

    def set_output(self, enable: bool) -> bool:
        """
        Aktiviert/Deaktiviert den Ausgang

        Args:
            enable: True für ON, False für OFF

        Returns:
            True bei Erfolg
        """
        data = [0x01 if enable else 0x00] + [0x00] * 21
        response = self._send_command(self.CMD_SET_OUTPUT, data)

        if response and response[2] == self.CMD_STATUS_RESPONSE:
            return response[3] == self.STATUS_SUCCESS
        return False

    def set_voltage(self, voltage: float) -> bool:
        """
        Setzt die Ausgangsspannung

        Args:
            voltage: Spannung in Volt (0.0 - 32.0V)

        Returns:
            True bei Erfolg
        """
        if not 0.0 <= voltage <= 32.0:
            raise ValueError("Spannung muss zwischen 0 und 32V liegen")

        # In Millivolt umrechnen
        voltage_mv = int(voltage * 1000)

        # Little-Endian 4-Byte Wert
        data = [
            voltage_mv & 0xFF,
            (voltage_mv >> 8) & 0xFF,
            (voltage_mv >> 16) & 0xFF,
            (voltage_mv >> 24) & 0xFF
        ] + [0x00] * 18

        response = self._send_command(self.CMD_SET_VOLTAGE, data)

        if response and response[2] == self.CMD_STATUS_RESPONSE:
            return response[3] == self.STATUS_SUCCESS

        return False

    def set_current(self, current: float) -> bool:
        """
        Setzt die Strombegrenzung

        Args:
            current: Strom in Ampere (0.0 - 6.0A)

        Returns:
            True bei Erfolg
        """
        if not 0.0 <= current <= 6.0:
            raise ValueError("Strom muss zwischen 0 und 6A liegen")

        # In Milliampere umrechnen
        current_ma = int(current * 1000)

        # Little-Endian 2-Byte Wert
        data = [
            current_ma & 0xFF,
            (current_ma >> 8) & 0xFF
        ] + [0x00] * 20

        response = self._send_command(self.CMD_SET_CURRENT, data)

        if response and response[2] == self.CMD_STATUS_RESPONSE:
            return response[3] == self.STATUS_SUCCESS

        return False

    def read_status(self) -> Optional[Dict]:
        """
        Liest den kompletten Status des Netzteils

        Returns:
            Dictionary mit Status-Informationen oder None bei Fehler
            Enthält:
            - actual_voltage: Aktuelle Ausgangsspannung (V)
            - actual_current: Aktueller Ausgangsstrom (A)
            - voltage_setpoint: Spannungs-Sollwert (V)
            - current_setpoint: Strom-Sollwert (A)
            - output_on: Ausgang aktiv (bool)
            - mode: Betriebsmodus ('CV', 'CC', 'Unreg', 'Unknown')
            - remote_mode: Remote-Steuerung aktiv (bool)
            - over_temp: Übertemperatur-Schutz aktiv (bool)
            - fan_speed: Lüftergeschwindigkeit (0-5)
        """
        data = [0x00] * 22
        response = self._send_command(self.CMD_READ_STATUS, data)

        if not response or response[2] != self.CMD_READ_STATUS:
            return None

        # Werte extrahieren (Little-Endian)
        actual_current_ma = response[3] | (response[4] << 8)
        actual_voltage_mv = response[5] | (response[6] << 8) | (response[7] << 16) | (response[8] << 24)
        status_byte = response[9]
        current_setpoint_ma = response[10] | (response[11] << 8)
        voltage_setpoint_mv = response[16] | (response[17] << 8) | (response[18] << 16) | (response[19] << 24)

        # Status-Byte dekodieren
        output_on = bool(status_byte & 0x01)
        over_temp = bool(status_byte & 0x02)
        mode = (status_byte >> 2) & 0x03
        fan_speed = (status_byte >> 4) & 0x07
        remote_mode = bool(status_byte & 0x80)

        mode_names = ['Unknown', 'CV', 'CC', 'Unreg']

        return {
            'actual_voltage': actual_voltage_mv / 1000.0,
            'actual_current': actual_current_ma / 1000.0,
            'voltage_setpoint': voltage_setpoint_mv / 1000.0,
            'current_setpoint': current_setpoint_ma / 1000.0,
            'output_on': output_on,
            'mode': mode_names[mode],
            'remote_mode': remote_mode,
            'over_temp': over_temp,
            'fan_speed': fan_speed
        }

    def get_voltage_current(self) -> Optional[Tuple[float, float]]:
        """
        Liest schnell nur Spannung und Strom (für kontinuierliches Monitoring)

        Returns:
            Tuple (Spannung in V, Strom in A) oder None bei Fehler
        """
        status = self.read_status()
        if status:
            return (status['actual_voltage'], status['actual_current'])
        return None


# Test-Funktion
if __name__ == "__main__":
    # Beispiel-Verwendung
    psu = BK1788B(port='COM3', baudrate=4800)

    if psu.connect():
        print("Verbindung hergestellt!")

        # Remote-Modus aktivieren
        if psu.set_remote_mode(True):
            print("Remote-Modus aktiviert")

        # Status lesen
        status = psu.read_status()
        if status:
            print(f"\nAktueller Status:")
            print(f"  Spannung: {status['actual_voltage']:.3f}V (Sollwert: {status['voltage_setpoint']:.3f}V)")
            print(f"  Strom:    {status['actual_current']:.3f}A (Sollwert: {status['current_setpoint']:.3f}A)")
            print(f"  Ausgang:  {'EIN' if status['output_on'] else 'AUS'}")
            print(f"  Modus:    {status['mode']}")
            print(f"  Remote:   {'Ja' if status['remote_mode'] else 'Nein'}")

        psu.disconnect()
        print("\nVerbindung getrennt")
    else:
        print("Verbindung fehlgeschlagen!")
