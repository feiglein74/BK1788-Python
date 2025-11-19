"""
BK Precision 1788B - GUI Anwendung mit Live-Graphen
Vollständige Steuerung und Überwachung des Netzteils mit Echtzeit-Datenvisualisierung
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import threading
import time
import json
import os
import signal
import sys
from collections import deque
from datetime import datetime
from bk1788b import BK1788B
import serial.tools.list_ports

try:
    from __version__ import __version__
except ImportError:
    __version__ = "unknown"


class PowerSupplyGUI:
    """Hauptfenster für die Netzteil-Steuerung"""

    def __init__(self, root):
        self.root = root
        self.root.title(f"BK Precision 1788B Steuerung v{__version__}")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        # Netzteil-Objekt
        self.psu = None
        self.connected = False
        self.monitoring = False
        self.monitor_thread = None

        # Thread-Synchronisation für serielle Kommunikation
        self.comm_lock = threading.Lock()
        self.force_gui_sync = False  # Flag für Force-Update nach Set-Operationen

        # Focus-Tracking: Verhindert Überschreiben während User tippt
        self.voltage_has_focus = False
        self.current_has_focus = False
        self.voltage_focus_timer = None  # Delay-Timer für FocusOut
        self.current_focus_timer = None

        # Set-Protection: Verhindert Überschreiben während Set-Operation
        self.setting_in_progress = False

        # Daten für Graphen (max. 500 Datenpunkte)
        self.max_points = 500
        self.timestamps = deque(maxlen=self.max_points)
        self.voltage_data = deque(maxlen=self.max_points)
        self.current_data = deque(maxlen=self.max_points)
        self.power_data = deque(maxlen=self.max_points)
        self.mode_data = deque(maxlen=self.max_points)  # Modus für Farbcodierung

        # Config-Datei für Einstellungen
        self.config_file = os.path.join(os.path.dirname(__file__), 'gui_config.json')

        # Letzte Einstellungen laden
        self.last_settings = self._load_settings()

        # GUI aufbauen
        self._create_widgets()

        # Update-Intervall für GUI (ms)
        self.update_interval = 100
        self._schedule_gui_update()

    def _create_widgets(self):
        """Erstellt alle GUI-Elemente"""

        # Hauptcontainer
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Grid-Konfiguration für Responsive Design
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # ===== Verbindungsbereich =====
        conn_frame = ttk.LabelFrame(main_frame, text="Verbindung", padding="10")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # COM-Port Auswahl mit automatischer Erkennung
        ttk.Label(conn_frame, text="COM-Port:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        # Liste verfügbarer Ports
        available_ports = self._get_available_ports()
        default_port = self.last_settings.get('port', available_ports[0] if available_ports else 'COM3')

        self.port_var = tk.StringVar(value=default_port)
        port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var,
                                   values=available_ports, width=12, state="readonly")
        port_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))

        # Refresh-Button für Ports
        ttk.Button(conn_frame, text="Aktualisieren", command=self._refresh_ports).grid(row=0, column=2, padx=(0, 20))

        # Baudrate Auswahl (nur gültige Werte für BK1788B)
        ttk.Label(conn_frame, text="Baudrate:").grid(row=0, column=3, sticky=tk.W, padx=(0, 5))

        # BK1788B unterstützt: 4800, 9600, 19200, 38400
        valid_baudrates = ["4800", "9600", "19200", "38400"]
        default_baudrate = self.last_settings.get('baudrate', '4800')

        self.baudrate_var = tk.StringVar(value=default_baudrate)
        self.baudrate_combo = ttk.Combobox(conn_frame, textvariable=self.baudrate_var,
                                            values=valid_baudrates,
                                            width=10, state="readonly")
        self.baudrate_combo.grid(row=0, column=4, sticky=tk.W, padx=(0, 20))

        self.connect_btn = ttk.Button(conn_frame, text="Verbinden", command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=5, padx=(0, 10))

        self.status_label = ttk.Label(conn_frame, text="● Nicht verbunden", foreground="red")
        self.status_label.grid(row=0, column=6, sticky=tk.W)

        # Port-Combo für Refresh speichern
        self.port_combo = port_combo

        # ===== Steuerungsbereich =====
        control_frame = ttk.LabelFrame(main_frame, text="Steuerung", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Spannungs-Steuerung
        ttk.Label(control_frame, text="Spannung (V):", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))

        voltage_frame = ttk.Frame(control_frame)
        voltage_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        self.voltage_var = tk.StringVar()  # StringVar statt DoubleVar für Komma-Unterstützung
        self.voltage_spinbox = ttk.Spinbox(voltage_frame, from_=0, to=32, increment=0.01,
                                       textvariable=self.voltage_var, width=10, format="%.2f")
        self.voltage_spinbox.grid(row=0, column=0, padx=(0, 10))
        self.voltage_spinbox.set("5.00")  # Startwert mit 2 Nachkommastellen
        self.voltage_spinbox.bind('<Return>', lambda e: self._set_voltage())  # Enter-Taste
        self.voltage_spinbox.bind('<FocusIn>', lambda e: self._voltage_focus_in())
        self.voltage_spinbox.bind('<FocusOut>', lambda e: self._voltage_focus_out())

        ttk.Button(voltage_frame, text="Setzen", command=self._set_voltage).grid(row=0, column=1)

        # Strom-Steuerung
        ttk.Label(control_frame, text="Strombegrenzung (A):", font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=(0, 5))

        current_frame = ttk.Frame(control_frame)
        current_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        self.current_var = tk.StringVar()  # StringVar statt DoubleVar für Komma-Unterstützung
        self.current_spinbox = ttk.Spinbox(current_frame, from_=0, to=6, increment=0.01,
                                       textvariable=self.current_var, width=10, format="%.2f")
        self.current_spinbox.grid(row=0, column=0, padx=(0, 10))
        self.current_spinbox.set("1.00")  # Startwert mit 2 Nachkommastellen
        self.current_spinbox.bind('<Return>', lambda e: self._set_current())  # Enter-Taste
        self.current_spinbox.bind('<FocusIn>', lambda e: self._current_focus_in())
        self.current_spinbox.bind('<FocusOut>', lambda e: self._current_focus_out())

        ttk.Button(current_frame, text="Setzen", command=self._set_current).grid(row=0, column=1)

        # Ausgang Ein/Aus - Button zeigt Status
        ttk.Separator(control_frame, orient=tk.HORIZONTAL).grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(control_frame, text="Ausgang:", font=("Arial", 10, "bold")).grid(
            row=5, column=0, sticky=tk.W, pady=(0, 5))

        self.output_btn = ttk.Button(control_frame, text="⬤ AUS",
                                      command=self._toggle_output, state=tk.DISABLED, width=20)
        self.output_btn.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Remote-Modus - Button zeigt Status
        ttk.Label(control_frame, text="Remote-Steuerung:", font=("Arial", 10, "bold")).grid(
            row=7, column=0, sticky=tk.W, pady=(0, 5))

        self.remote_btn = ttk.Button(control_frame, text="⬤ Inaktiv",
                                      command=self._toggle_remote, state=tk.DISABLED, width=20)
        self.remote_btn.grid(row=8, column=0, sticky=(tk.W, tk.E))

        # ===== Anzeigebereich =====
        display_frame = ttk.LabelFrame(main_frame, text="Aktuelle Werte", padding="10")
        display_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(10, 0))

        # Große Anzeigen für Spannung und Strom
        # Spannung mit 3. Nachkommastelle gedimmt (Netzteil hat nur 2 Stellen Genauigkeit)
        voltage_frame = ttk.Frame(display_frame)
        voltage_frame.grid(row=0, column=0, pady=(10, 5))

        self.voltage_main = tk.Label(voltage_frame, text="0.00", font=("Arial", 24, "bold"),
                                      fg="blue")
        self.voltage_main.pack(side=tk.LEFT)

        self.voltage_faint = tk.Label(voltage_frame, text="0", font=("Arial", 24, "bold"),
                                       fg="#8080FF")  # Helles Blau
        self.voltage_faint.pack(side=tk.LEFT)

        self.voltage_unit = tk.Label(voltage_frame, text=" V", font=("Arial", 24, "bold"),
                                      fg="blue")
        self.voltage_unit.pack(side=tk.LEFT)

        ttk.Label(display_frame, text="Spannung").grid(row=1, column=0, pady=(0, 15))

        # Strom mit 3. Nachkommastelle gedimmt
        current_frame = ttk.Frame(display_frame)
        current_frame.grid(row=2, column=0, pady=(10, 5))

        self.current_main = tk.Label(current_frame, text="0.00", font=("Arial", 24, "bold"),
                                      fg="red")
        self.current_main.pack(side=tk.LEFT)

        self.current_faint = tk.Label(current_frame, text="0", font=("Arial", 24, "bold"),
                                       fg="#FF8080")  # Helles Rot
        self.current_faint.pack(side=tk.LEFT)

        self.current_unit = tk.Label(current_frame, text=" A", font=("Arial", 24, "bold"),
                                      fg="red")
        self.current_unit.pack(side=tk.LEFT)

        ttk.Label(display_frame, text="Strom").grid(row=3, column=0, pady=(0, 15))

        # Leistung - alle 3 Nachkommastellen, da berechnet
        self.power_display = ttk.Label(display_frame, text="0.000 W",
                                        font=("Arial", 20), foreground="green")
        self.power_display.grid(row=4, column=0, pady=(10, 5))

        ttk.Label(display_frame, text="Leistung").grid(row=5, column=0, pady=(0, 15))

        # Status-Informationen
        ttk.Separator(display_frame, orient=tk.HORIZONTAL).grid(row=6, column=0, sticky=(tk.W, tk.E), pady=10)

        self.mode_label = ttk.Label(display_frame, text="Modus: --", font=("Arial", 10))
        self.mode_label.grid(row=7, column=0, sticky=tk.W, pady=2)

        self.temp_label = ttk.Label(display_frame, text="Übertemperatur: --", font=("Arial", 10))
        self.temp_label.grid(row=8, column=0, sticky=tk.W, pady=2)

        self.fan_label = ttk.Label(display_frame, text="Lüfter: --", font=("Arial", 10))
        self.fan_label.grid(row=9, column=0, sticky=tk.W, pady=2)

        self.max_voltage_label = ttk.Label(display_frame, text="Max. Spannung: --", font=("Arial", 10))
        self.max_voltage_label.grid(row=10, column=0, sticky=tk.W, pady=2)

        # ===== Graph-Bereich =====
        graph_frame = ttk.LabelFrame(main_frame, text="Live-Messdaten", padding="10")
        graph_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Matplotlib Figure erstellen mit mehr Platz für Beschriftungen
        self.fig = Figure(figsize=(10, 5), dpi=100)

        # Subplots mit mehr Abstand erstellen
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)

        # Spannung/Strom Plot mit zwei Y-Achsen
        # Linke Y-Achse: Spannung (0-32V)
        self.ax1.set_ylabel('Spannung (V)', fontsize=10, color='blue')
        self.ax1.tick_params(axis='y', labelcolor='blue', labelsize=9)
        self.ax1.set_xlim(0, 10)
        self.ax1.set_ylim(0, 32)  # Max. 32V
        self.ax1.grid(True, alpha=0.3)

        # Rechte Y-Achse: Strom (0-6A)
        self.ax1_right = self.ax1.twinx()
        self.ax1_right.set_ylabel('Strom (A)', fontsize=10, color='red')
        self.ax1_right.tick_params(axis='y', labelcolor='red', labelsize=9)
        self.ax1_right.set_ylim(0, 6)  # Max. 6A

        # Stromlinie auf rechter Y-Achse
        self.line_current, = self.ax1_right.plot([], [], 'r-', linewidth=2)

        # Legende für Spannungs-Modi (oben links)
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='blue', linewidth=2, label='Spannung (CV)'),
            Line2D([0], [0], color='orange', linewidth=2, label='Spannung (CC)'),
            Line2D([0], [0], color='red', linewidth=2, label='Strom (A)')
        ]
        self.ax1.legend(handles=legend_elements, loc='upper left', fontsize=9)

        # Collection für Spannungs-Segmente (wird dynamisch gefüllt)
        self.voltage_segments = []

        # Leistungs-Plot
        self.line_power, = self.ax2.plot([], [], 'g-', label='Leistung (W)', linewidth=2)
        self.ax2.set_xlabel('Zeit (s)', fontsize=10)
        self.ax2.set_ylabel('Leistung (W)', fontsize=10)
        self.ax2.legend(loc='upper left', fontsize=9)
        self.ax2.grid(True, alpha=0.3)
        self.ax2.tick_params(axis='both', labelsize=9)
        self.ax2.set_xlim(0, 10)  # Initiale Achsenlimits
        self.ax2.set_ylim(0, 10)

        # Tight layout mit mehr Platz für Beschriftungen
        # left/right/top/bottom definieren die Ränder für Beschriftungen
        self.fig.subplots_adjust(left=0.08, right=0.92, top=0.96, bottom=0.08, hspace=0.25)

        # Canvas für Matplotlib
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Navigation-Toolbar (Zoom, Pan, Scroll, Home, Save)
        toolbar_frame = ttk.Frame(graph_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        # Startzeit für relative Zeitachse
        self.start_time = None

    def _voltage_focus_in(self):
        """Spannung-Spinbox hat Focus erhalten"""
        # Timer canceln falls gerade läuft
        if self.voltage_focus_timer:
            self.root.after_cancel(self.voltage_focus_timer)
            self.voltage_focus_timer = None
        # Sofort Focus setzen
        self.voltage_has_focus = True

    def _voltage_focus_out(self):
        """Spannung-Spinbox hat Focus verloren - mit Delay"""
        # Focus erst nach 200ms als verloren markieren
        # Gibt Button-Click Zeit, setting_in_progress zu setzen
        if self.voltage_focus_timer:
            self.root.after_cancel(self.voltage_focus_timer)
        self.voltage_focus_timer = self.root.after(200, lambda: setattr(self, 'voltage_has_focus', False))

    def _current_focus_in(self):
        """Strom-Spinbox hat Focus erhalten"""
        # Timer canceln falls gerade läuft
        if self.current_focus_timer:
            self.root.after_cancel(self.current_focus_timer)
            self.current_focus_timer = None
        # Sofort Focus setzen
        self.current_has_focus = True

    def _current_focus_out(self):
        """Strom-Spinbox hat Focus verloren - mit Delay"""
        # Focus erst nach 200ms als verloren markieren
        # Gibt Button-Click Zeit, setting_in_progress zu setzen
        if self.current_focus_timer:
            self.root.after_cancel(self.current_focus_timer)
        self.current_focus_timer = self.root.after(200, lambda: setattr(self, 'current_has_focus', False))

    def _toggle_connection(self):
        """Verbindung herstellen/trennen"""
        if not self.connected:
            # Verbinden
            port = self.port_var.get()
            try:
                baudrate = int(self.baudrate_var.get())
            except ValueError:
                messagebox.showerror("Fehler", "Ungültige Baudrate")
                return

            self.psu = BK1788B(port=port, baudrate=baudrate)

            if self.psu.connect():
                self.connected = True
                self.status_label.config(text="● Verbunden", foreground="green")
                self.connect_btn.config(text="Trennen")
                self.output_btn.config(state=tk.NORMAL)
                self.remote_btn.config(state=tk.NORMAL)

                # Einstellungen sofort speichern (für nächsten Start)
                self._save_settings()

                # Status lesen und Remote-Modus ausschalten falls noch aktiv
                # (könnte von vorherigem Programmlauf noch gesperrt sein)
                # Nutzt Lock obwohl Monitoring noch nicht läuft (für Konsistenz)
                with self.comm_lock:
                    status = self.psu.read_status()
                    if status:
                        if status['remote_mode']:
                            # Netzteil entsperren
                            self.psu.set_remote_mode(False)
                            # Nochmal Status lesen für aktuelle Sollwerte
                            status = self.psu.read_status()

                        if status:
                            # Sollwerte vom Netzteil in GUI übernehmen (formatiert mit 2 Nachkommastellen)
                            self.voltage_var.set(f"{status['voltage_setpoint']:.2f}")
                            self.current_var.set(f"{status['current_setpoint']:.2f}")

                # Monitoring starten
                self._start_monitoring()

                # Kein Popup - Status-Label zeigt bereits "Verbunden"
            else:
                # Nur bei Fehler Meldung zeigen
                messagebox.showerror("Fehler", f"Verbindung zu {port} fehlgeschlagen")
        else:
            # Trennen
            self._stop_monitoring()

            if self.psu:
                # Remote-Modus ausschalten damit Frontpanel wieder bedienbar ist
                # Lock nutzen falls Monitor-Thread gerade noch läuft
                try:
                    with self.comm_lock:
                        self.psu.set_remote_mode(False)
                except:
                    pass  # Ignorieren falls Kommunikation schon unterbrochen

                self.psu.disconnect()
                self.psu = None

            self.connected = False
            self.status_label.config(text="● Nicht verbunden", foreground="red")
            self.connect_btn.config(text="Verbinden")
            self.output_btn.config(state=tk.DISABLED)
            self.remote_btn.config(state=tk.DISABLED)

    def _start_monitoring(self):
        """Startet den Monitoring-Thread"""
        if not self.monitoring:
            self.monitoring = True
            self.start_time = time.time()
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

    def _stop_monitoring(self):
        """Stoppt den Monitoring-Thread"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)  # Kürzerer Timeout
            # Wenn Thread nicht beendet, einfach weitermachen (daemon=True killt ihn automatisch)
        self.monitor_thread = None

    def _monitor_loop(self):
        """Monitoring-Schleife (läuft in separatem Thread)"""
        while self.monitoring and self.connected:
            try:
                # Serielle Kommunikation mit Lock schützen
                with self.comm_lock:
                    status = self.psu.read_status()

                if status:
                    # Zeitstempel hinzufügen
                    current_time = time.time() - self.start_time

                    # Daten speichern
                    self.timestamps.append(current_time)
                    self.voltage_data.append(status['actual_voltage'])
                    self.current_data.append(status['actual_current'])
                    self.power_data.append(status['actual_voltage'] * status['actual_current'])
                    self.mode_data.append(status['mode'])  # Modus speichern für Farbcodierung

                    # Status zwischenspeichern für GUI-Update
                    self.last_status = status

                # Pause zwischen Messungen (10 Hz)
                time.sleep(0.1)

            except Exception as e:
                print(f"Fehler beim Monitoring: {e}")
                time.sleep(1)

    def _schedule_gui_update(self):
        """Plant regelmäßige GUI-Updates"""
        self._update_gui()
        self.root.after(self.update_interval, self._schedule_gui_update)

    def _update_gui(self):
        """Aktualisiert GUI-Elemente (läuft im Hauptthread)"""
        if hasattr(self, 'last_status') and self.last_status:
            status = self.last_status

            # Anzeigen aktualisieren mit geteilter Formatierung
            # Spannung: XX.XX in voller Farbe, letzte Stelle gedimmt
            voltage = status['actual_voltage']
            voltage_main = f"{voltage:.2f}"  # z.B. "5.00"
            voltage_last = str(int((voltage * 1000) % 10))  # Letzte Stelle
            self.voltage_main.config(text=voltage_main)
            self.voltage_faint.config(text=voltage_last)

            # Strom: X.XX in voller Farbe, letzte Stelle gedimmt
            current = status['actual_current']
            current_main = f"{current:.2f}"  # z.B. "1.23"
            current_last = str(int((current * 1000) % 10))  # Letzte Stelle
            self.current_main.config(text=current_main)
            self.current_faint.config(text=current_last)

            # Leistung: Alle 3 Nachkommastellen (berechnet, kein direkter Messwert)
            power = voltage * current
            self.power_display.config(text=f"{power:.3f} W")

            # Status-Labels aktualisieren (rechte Seite - nur Modus und Temp)
            # Modus mit Farbcodierung: CV=Blau, CC=Orange, Unreg=Grau
            mode = status['mode']
            self.mode_label.config(text=f"Modus: {mode}")

            if mode == 'CV':
                self.mode_label.config(foreground="blue")
            elif mode == 'CC':
                self.mode_label.config(foreground="orange")
            else:
                self.mode_label.config(foreground="gray")

            self.temp_label.config(text=f"Übertemperatur: {'WARNUNG!' if status['over_temp'] else 'OK'}")

            if status['over_temp']:
                self.temp_label.config(foreground="red")
            else:
                self.temp_label.config(foreground="black")

            # Lüfter-Geschwindigkeit (0-5: 0=Aus, 5=Maximum)
            fan_speed = status['fan_speed']
            if fan_speed == 0:
                self.fan_label.config(text="Lüfter: Aus", foreground="gray")
            else:
                self.fan_label.config(text=f"Lüfter: Stufe {fan_speed}/5", foreground="green")

            # Maximale Spannung
            self.max_voltage_label.config(text=f"Max. Spannung: {status['max_voltage']:.1f}V", foreground="black")

            # Button-Status aktualisieren (Button zeigt aktuellen Zustand)
            if status['output_on']:
                self.output_btn.config(text="● EIN")
            else:
                self.output_btn.config(text="⬤ AUS")

            if status['remote_mode']:
                self.remote_btn.config(text="● Aktiv")
            else:
                self.remote_btn.config(text="⬤ Inaktiv")

            # Sollwerte-Synchronisation: Remote-Modus aus ODER Force-Sync nach Set-Operation
            if not status['remote_mode'] or self.force_gui_sync:
                # Force-Sync: Immer aktualisieren (nach Set-Operation)
                # Normal-Sync: Nur wenn Differenz > 0.01 (Frontpanel-Änderung erkannt)
                # ABER: Nicht überschreiben wenn User gerade tippt ODER gerade "Setzen" geklickt hat

                # Spannung: Nur aktualisieren wenn KEIN Focus UND NICHT setting (außer Force-Sync)
                if (not self.voltage_has_focus and not self.setting_in_progress) or self.force_gui_sync:
                    try:
                        current_gui_voltage = float(self.voltage_var.get().replace(',', '.'))
                        netzteil_voltage = status['voltage_setpoint']
                        # Bei Force-Sync ODER signifikanter Differenz aktualisieren
                        if self.force_gui_sync or abs(current_gui_voltage - netzteil_voltage) > 0.01:
                            self.voltage_var.set(f"{netzteil_voltage:.2f}")
                    except (ValueError, AttributeError):
                        # Ungültiger Wert in GUI - überschreiben mit Netzteil-Wert
                        self.voltage_var.set(f"{status['voltage_setpoint']:.2f}")

                # Strom: Nur aktualisieren wenn KEIN Focus UND NICHT setting (außer Force-Sync)
                if (not self.current_has_focus and not self.setting_in_progress) or self.force_gui_sync:
                    try:
                        current_gui_current = float(self.current_var.get().replace(',', '.'))
                        netzteil_current = status['current_setpoint']
                        # Bei Force-Sync ODER signifikanter Differenz aktualisieren
                        if self.force_gui_sync or abs(current_gui_current - netzteil_current) > 0.01:
                            self.current_var.set(f"{netzteil_current:.2f}")
                    except (ValueError, AttributeError):
                        # Ungültiger Wert in GUI - überschreiben mit Netzteil-Wert
                        self.current_var.set(f"{status['current_setpoint']:.2f}")

                # Force-Sync Flag zurücksetzen nach Aktualisierung
                self.force_gui_sync = False

        # Graphen aktualisieren
        if len(self.timestamps) > 0:
            self._update_plots()

    def _update_plots(self):
        """Aktualisiert die Matplotlib-Graphen"""
        times = list(self.timestamps)
        voltages = list(self.voltage_data)
        currents = list(self.current_data)
        powers = list(self.power_data)
        modes = list(self.mode_data)

        # Alte Spannungs-Segmente entfernen
        for segment in self.voltage_segments:
            segment.remove()
        self.voltage_segments.clear()

        # Spannungs-Segmente nach Modus gruppieren und einfärben
        if len(times) > 1 and len(modes) > 0:
            i = 0
            while i < len(times):
                # Segment-Start finden
                start_idx = i
                current_mode = modes[i] if i < len(modes) else 'CV'

                # Solange gleicher Modus, Segment erweitern
                while i < len(times) - 1 and i + 1 < len(modes) and modes[i + 1] == current_mode:
                    i += 1

                # Segment-Ende: i+1 für Überlappung mit nächstem Segment
                # Aber nicht über das Ende hinaus
                end_idx = min(i + 2, len(times))

                # Farbe basierend auf Modus
                if current_mode == 'CC':
                    color = 'orange'
                elif current_mode == 'CV':
                    color = 'blue'
                else:
                    color = 'gray'

                # Segment zeichnen (mit einem Punkt Überlappung)
                segment, = self.ax1.plot(
                    times[start_idx:end_idx],
                    voltages[start_idx:end_idx],
                    color=color,
                    linewidth=2
                )
                self.voltage_segments.append(segment)

                i += 1

        # Strom Plot aktualisieren (bleibt immer rot)
        self.line_current.set_data(times, currents)

        # Leistungs-Plot aktualisieren
        self.line_power.set_data(times, powers)

        # Nur automatisch skalieren wenn Toolbar im Home-Modus ist
        # (d.h. Benutzer hat nicht gezoomt/gepanned)
        if len(times) > 0 and self.toolbar.mode == '':
            # Auto-Skalierung nur wenn nicht manuell gezoomt
            self.ax1.set_xlim(min(times), max(times))
            self.ax2.set_xlim(min(times), max(times))

            # Spannung Y-Achse (links)
            if len(voltages) > 0:
                v_max = max(voltages) if max(voltages) > 0 else 1
                self.ax1.set_ylim(0, min(v_max * 1.1, 32))  # Max. 32V

            # Strom Y-Achse (rechts)
            if len(currents) > 0:
                c_max = max(currents) if max(currents) > 0 else 1
                self.ax1_right.set_ylim(0, min(c_max * 1.1, 6))  # Max. 6A

            # Leistung Y-Achse
            if len(powers) > 0:
                p_max = max(powers) if max(powers) > 0 else 1
                self.ax2.set_ylim(0, p_max * 1.1)

        # Canvas neu zeichnen
        self.canvas.draw_idle()

    def _set_voltage(self):
        """Setzt die Ausgangsspannung"""
        if not self.connected:
            return

        try:
            # Focus-Timer sofort canceln (falls FocusOut gerade verzögert läuft)
            if self.voltage_focus_timer:
                self.root.after_cancel(self.voltage_focus_timer)
                self.voltage_focus_timer = None

            # SOFORT Flag setzen: Verhindert Überschreiben während Set-Operation
            self.setting_in_progress = True
            self.voltage_has_focus = False  # Focus ist jetzt definitiv weg

            # Komma in Punkt umwandeln (deutsche Tastatur)
            voltage_str = self.voltage_var.get().replace(',', '.')
            voltage = float(voltage_str)

            # Gesamte Set-Operation mit Lock schützen
            with self.comm_lock:
                # Status prüfen: Remote-Modus aktiv?
                status = self.psu.read_status()
                if not status:
                    messagebox.showerror("Fehler", "Status konnte nicht gelesen werden")
                    return

                remote_was_off = not status['remote_mode']

                # Falls Remote-Modus aus: temporär aktivieren
                if remote_was_off:
                    if not self.psu.set_remote_mode(True):
                        messagebox.showerror("Fehler", "Remote-Modus konnte nicht aktiviert werden")
                        return

                # Spannung setzen
                success = self.psu.set_voltage(voltage)

                # Remote-Modus wieder deaktivieren falls vorher aus
                if remote_was_off:
                    self.psu.set_remote_mode(False)

                # Status neu lesen für Verifikation
                final_status = self.psu.read_status()

                if not success or not final_status:
                    # Bei Fehler: GUI auf aktuellen Netzteil-Wert zurücksetzen
                    if final_status:
                        self.voltage_var.set(f"{final_status['voltage_setpoint']:.2f}")
                    messagebox.showerror("Fehler", "Spannung konnte nicht gesetzt werden")
                else:
                    # Erfolg: Force-Sync auslösen für sofortige GUI-Aktualisierung
                    self.force_gui_sync = True
                    self.last_status = final_status

        except ValueError as e:
            messagebox.showerror("Fehler", f"Ungültiger Wert: {e}")
        finally:
            # Flag IMMER zurücksetzen (auch bei Fehler)
            self.setting_in_progress = False

    def _set_current(self):
        """Setzt die Strombegrenzung"""
        if not self.connected:
            return

        try:
            # Focus-Timer sofort canceln (falls FocusOut gerade verzögert läuft)
            if self.current_focus_timer:
                self.root.after_cancel(self.current_focus_timer)
                self.current_focus_timer = None

            # SOFORT Flag setzen: Verhindert Überschreiben während Set-Operation
            self.setting_in_progress = True
            self.current_has_focus = False  # Focus ist jetzt definitiv weg

            # Komma in Punkt umwandeln (deutsche Tastatur)
            current_str = self.current_var.get().replace(',', '.')
            current = float(current_str)

            # Gesamte Set-Operation mit Lock schützen
            with self.comm_lock:
                # Status prüfen: Remote-Modus aktiv?
                status = self.psu.read_status()
                if not status:
                    messagebox.showerror("Fehler", "Status konnte nicht gelesen werden")
                    return

                remote_was_off = not status['remote_mode']

                # Falls Remote-Modus aus: temporär aktivieren
                if remote_was_off:
                    if not self.psu.set_remote_mode(True):
                        messagebox.showerror("Fehler", "Remote-Modus konnte nicht aktiviert werden")
                        return

                # Strom setzen
                success = self.psu.set_current(current)

                # Remote-Modus wieder deaktivieren falls vorher aus
                if remote_was_off:
                    self.psu.set_remote_mode(False)

                # Status neu lesen für Verifikation
                final_status = self.psu.read_status()

                if not success or not final_status:
                    # Bei Fehler: GUI auf aktuellen Netzteil-Wert zurücksetzen
                    if final_status:
                        self.current_var.set(f"{final_status['current_setpoint']:.2f}")
                    messagebox.showerror("Fehler", "Strom konnte nicht gesetzt werden")
                else:
                    # Erfolg: Force-Sync auslösen für sofortige GUI-Aktualisierung
                    self.force_gui_sync = True
                    self.last_status = final_status

        except ValueError as e:
            messagebox.showerror("Fehler", f"Ungültiger Wert: {e}")
        finally:
            # Flag IMMER zurücksetzen (auch bei Fehler)
            self.setting_in_progress = False

    def _toggle_output(self):
        """Schaltet den Ausgang ein/aus"""
        if not self.connected or not hasattr(self, 'last_status'):
            return

        current_state = self.last_status.get('output_on', False)
        new_state = not current_state

        # Gesamte Set-Operation mit Lock schützen
        with self.comm_lock:
            # Status prüfen: Remote-Modus aktiv?
            status = self.psu.read_status()
            if not status:
                messagebox.showerror("Fehler", "Status konnte nicht gelesen werden")
                return

            remote_was_off = not status['remote_mode']

            # Falls Remote-Modus aus: temporär aktivieren
            if remote_was_off:
                if not self.psu.set_remote_mode(True):
                    messagebox.showerror("Fehler", "Remote-Modus konnte nicht aktiviert werden")
                    return

            # Ausgang schalten
            success = self.psu.set_output(new_state)

            # Remote-Modus wieder deaktivieren falls vorher aus
            if remote_was_off:
                self.psu.set_remote_mode(False)

            # Status neu lesen für Verifikation
            final_status = self.psu.read_status()

            if not success or not final_status:
                messagebox.showerror("Fehler", "Ausgang konnte nicht geschaltet werden")
            else:
                # Erfolg: Force-Sync auslösen
                self.force_gui_sync = True
                self.last_status = final_status

    def _toggle_remote(self):
        """Schaltet den Remote-Modus ein/aus"""
        if not self.connected or not hasattr(self, 'last_status'):
            return

        current_state = self.last_status.get('remote_mode', False)
        new_state = not current_state

        # Gesamte Remote-Toggle-Operation mit Lock schützen
        with self.comm_lock:
            success = self.psu.set_remote_mode(new_state)

            if success:
                # Wenn Remote-Modus aktiviert wird: GUI-Werte ans Netzteil senden
                if new_state:
                    try:
                        voltage = float(self.voltage_var.get().replace(',', '.'))
                        current = float(self.current_var.get().replace(',', '.'))
                        self.psu.set_voltage(voltage)
                        self.psu.set_current(current)
                    except ValueError:
                        pass  # Ungültige Werte ignorieren

                # Status neu lesen für Verifikation
                final_status = self.psu.read_status()
                if final_status:
                    self.force_gui_sync = True
                    self.last_status = final_status
            else:
                # Nur bei Fehler Meldung zeigen
                messagebox.showerror("Fehler", "Remote-Modus konnte nicht geschaltet werden")

    def _get_available_ports(self):
        """Ermittelt alle verfügbaren COM-Ports"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        return port_list if port_list else ['COM3']  # Fallback wenn keine Ports gefunden

    def _refresh_ports(self):
        """Aktualisiert die Liste der verfügbaren COM-Ports"""
        available_ports = self._get_available_ports()
        self.port_combo['values'] = available_ports

        # Wenn aktueller Port nicht mehr verfügbar, ersten nehmen
        if self.port_var.get() not in available_ports and available_ports:
            self.port_var.set(available_ports[0])

    def _load_settings(self):
        """Lädt die letzten Verbindungseinstellungen"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der Einstellungen: {e}")

        # Defaults wenn Datei nicht existiert oder Fehler
        return {'port': 'COM3', 'baudrate': '4800'}

    def _save_settings(self):
        """Speichert die aktuellen Verbindungseinstellungen"""
        try:
            settings = {
                'port': self.port_var.get(),
                'baudrate': self.baudrate_var.get()
            }
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Einstellungen: {e}")

    def on_closing(self):
        """Wird beim Schließen des Fensters aufgerufen"""
        # Einstellungen speichern
        try:
            self._save_settings()
        except:
            pass

        if self.connected:
            # Monitoring stoppen (non-blocking)
            self.monitoring = False
            self.connected = False

            # Remote-Modus ausschalten damit Frontpanel wieder bedienbar ist
            if self.psu:
                try:
                    with self.comm_lock:
                        self.psu.set_remote_mode(False)
                except:
                    pass  # Ignorieren falls Kommunikation schon unterbrochen

                try:
                    self.psu.disconnect()
                except:
                    pass

        # Thread wird automatisch beendet (daemon=True)
        try:
            self.root.destroy()
        except:
            pass


def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = PowerSupplyGUI(root)

    # Cleanup bei Strg+C (SIGINT)
    def signal_handler(sig, frame):
        print("\nProgramm wird beendet...")
        app.on_closing()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
