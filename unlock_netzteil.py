"""
Hilfsskript: Schaltet Remote-Modus am BK1788B aus
Verwendung wenn das Netzteil gesperrt ist nach Programmabsturz
"""

from bk1788b import BK1788B
import sys

def unlock_psu(port='COM3', baudrate=4800):
    """Schaltet Remote-Modus aus um Frontpanel freizugeben"""
    print(f"Verbinde mit {port} @ {baudrate} Baud...")

    psu = BK1788B(port=port, baudrate=baudrate)

    if psu.connect():
        print("Verbunden!")

        # Status lesen
        status = psu.read_status()
        if status:
            print(f"Remote-Modus: {'EIN' if status['remote_mode'] else 'AUS'}")

            if status['remote_mode']:
                print("Schalte Remote-Modus aus...")
                if psu.set_remote_mode(False):
                    print("✓ Remote-Modus ausgeschaltet - Frontpanel ist jetzt bedienbar!")
                else:
                    print("✗ Fehler beim Ausschalten")
            else:
                print("Remote-Modus ist bereits aus")

        psu.disconnect()
        print("Verbindung getrennt")
    else:
        print(f"✗ Verbindung zu {port} fehlgeschlagen!")
        print("Prüfe COM-Port und Baudrate")
        return False

    return True

if __name__ == "__main__":
    # COM-Port als Parameter erlauben
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 4800

    unlock_psu(port, baudrate)
