"""
BK Precision 1788B - GUI Anwendung mit Live-Graphen
Vollständige Steuerung und Überwachung des Netzteils mit Echtzeit-Datenvisualisierung
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
from collections import deque
from datetime import datetime
from bk1788b import BK1788B


class PowerSupplyGUI:
    """Hauptfenster für die Netzteil-Steuerung"""

    def __init__(self, root):
        self.root = root
        self.root.title("BK Precision 1788B Steuerung")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        # Netzteil-Objekt
        self.psu = None
        self.connected = False
        self.monitoring = False
        self.monitor_thread = None

        # Daten für Graphen (max. 500 Datenpunkte)
        self.max_points = 500
        self.timestamps = deque(maxlen=self.max_points)
        self.voltage_data = deque(maxlen=self.max_points)
        self.current_data = deque(maxlen=self.max_points)
        self.power_data = deque(maxlen=self.max_points)

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

        ttk.Label(conn_frame, text="COM-Port:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.port_var = tk.StringVar(value="COM3")
        port_entry = ttk.Entry(conn_frame, textvariable=self.port_var, width=10)
        port_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(conn_frame, text="Baudrate:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.baudrate_var = tk.StringVar(value="4800")
        baudrate_combo = ttk.Combobox(conn_frame, textvariable=self.baudrate_var,
                                       values=["4800", "9600", "19200", "38400"],
                                       width=10, state="readonly")
        baudrate_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        self.connect_btn = ttk.Button(conn_frame, text="Verbinden", command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=(0, 10))

        self.status_label = ttk.Label(conn_frame, text="● Nicht verbunden", foreground="red")
        self.status_label.grid(row=0, column=5, sticky=tk.W)

        # ===== Steuerungsbereich =====
        control_frame = ttk.LabelFrame(main_frame, text="Steuerung", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Spannungs-Steuerung
        ttk.Label(control_frame, text="Spannung (V):", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))

        voltage_frame = ttk.Frame(control_frame)
        voltage_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        self.voltage_var = tk.DoubleVar(value=5.0)
        voltage_spinbox = ttk.Spinbox(voltage_frame, from_=0, to=32, increment=0.1,
                                       textvariable=self.voltage_var, width=10)
        voltage_spinbox.grid(row=0, column=0, padx=(0, 10))

        ttk.Button(voltage_frame, text="Setzen", command=self._set_voltage).grid(row=0, column=1)

        # Strom-Steuerung
        ttk.Label(control_frame, text="Strombegrenzung (A):", font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=(0, 5))

        current_frame = ttk.Frame(control_frame)
        current_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        self.current_var = tk.DoubleVar(value=1.0)
        current_spinbox = ttk.Spinbox(current_frame, from_=0, to=6, increment=0.01,
                                       textvariable=self.current_var, width=10)
        current_spinbox.grid(row=0, column=0, padx=(0, 10))

        ttk.Button(current_frame, text="Setzen", command=self._set_current).grid(row=0, column=1)

        # Ausgang Ein/Aus
        ttk.Separator(control_frame, orient=tk.HORIZONTAL).grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)

        self.output_btn = ttk.Button(control_frame, text="Ausgang EIN",
                                      command=self._toggle_output, state=tk.DISABLED)
        self.output_btn.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Remote-Modus
        self.remote_btn = ttk.Button(control_frame, text="Remote-Modus EIN",
                                      command=self._toggle_remote, state=tk.DISABLED)
        self.remote_btn.grid(row=6, column=0, sticky=(tk.W, tk.E))

        # ===== Anzeigebereich =====
        display_frame = ttk.LabelFrame(main_frame, text="Aktuelle Werte", padding="10")
        display_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(10, 0))

        # Große Anzeigen für Spannung und Strom
        self.voltage_display = ttk.Label(display_frame, text="0.000 V",
                                          font=("Arial", 24, "bold"), foreground="blue")
        self.voltage_display.grid(row=0, column=0, pady=(10, 5))

        ttk.Label(display_frame, text="Spannung").grid(row=1, column=0, pady=(0, 15))

        self.current_display = ttk.Label(display_frame, text="0.000 A",
                                          font=("Arial", 24, "bold"), foreground="red")
        self.current_display.grid(row=2, column=0, pady=(10, 5))

        ttk.Label(display_frame, text="Strom").grid(row=3, column=0, pady=(0, 15))

        self.power_display = ttk.Label(display_frame, text="0.000 W",
                                        font=("Arial", 20), foreground="green")
        self.power_display.grid(row=4, column=0, pady=(10, 5))

        ttk.Label(display_frame, text="Leistung").grid(row=5, column=0, pady=(0, 15))

        # Status-Informationen
        ttk.Separator(display_frame, orient=tk.HORIZONTAL).grid(row=6, column=0, sticky=(tk.W, tk.E), pady=10)

        self.mode_label = ttk.Label(display_frame, text="Modus: --", font=("Arial", 10))
        self.mode_label.grid(row=7, column=0, sticky=tk.W, pady=2)

        self.output_status_label = ttk.Label(display_frame, text="Ausgang: --", font=("Arial", 10))
        self.output_status_label.grid(row=8, column=0, sticky=tk.W, pady=2)

        self.remote_status_label = ttk.Label(display_frame, text="Remote: --", font=("Arial", 10))
        self.remote_status_label.grid(row=9, column=0, sticky=tk.W, pady=2)

        self.temp_label = ttk.Label(display_frame, text="Übertemperatur: --", font=("Arial", 10))
        self.temp_label.grid(row=10, column=0, sticky=tk.W, pady=2)

        # ===== Graph-Bereich =====
        graph_frame = ttk.LabelFrame(main_frame, text="Live-Messdaten", padding="10")
        graph_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Matplotlib Figure erstellen
        self.fig = Figure(figsize=(10, 5), dpi=100)

        # Zwei Subplots: Spannung/Strom und Leistung
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)

        # Spannung/Strom Plot
        self.line_voltage, = self.ax1.plot([], [], 'b-', label='Spannung (V)', linewidth=2)
        self.line_current, = self.ax1.plot([], [], 'r-', label='Strom (A)', linewidth=2)
        self.ax1.set_ylabel('Spannung (V) / Strom (A)')
        self.ax1.legend(loc='upper left')
        self.ax1.grid(True, alpha=0.3)

        # Leistungs-Plot
        self.line_power, = self.ax2.plot([], [], 'g-', label='Leistung (W)', linewidth=2)
        self.ax2.set_xlabel('Zeit (s)')
        self.ax2.set_ylabel('Leistung (W)')
        self.ax2.legend(loc='upper left')
        self.ax2.grid(True, alpha=0.3)

        self.fig.tight_layout()

        # Canvas für Matplotlib
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Startzeit für relative Zeitachse
        self.start_time = None

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

                # Monitoring starten
                self._start_monitoring()

                messagebox.showinfo("Erfolg", f"Verbunden mit {port}")
            else:
                messagebox.showerror("Fehler", f"Verbindung zu {port} fehlgeschlagen")
        else:
            # Trennen
            self._stop_monitoring()

            if self.psu:
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
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
            self.monitor_thread = None

    def _monitor_loop(self):
        """Monitoring-Schleife (läuft in separatem Thread)"""
        while self.monitoring and self.connected:
            try:
                status = self.psu.read_status()
                if status:
                    # Zeitstempel hinzufügen
                    current_time = time.time() - self.start_time

                    # Daten speichern
                    self.timestamps.append(current_time)
                    self.voltage_data.append(status['actual_voltage'])
                    self.current_data.append(status['actual_current'])
                    self.power_data.append(status['actual_voltage'] * status['actual_current'])

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

            # Anzeigen aktualisieren
            self.voltage_display.config(text=f"{status['actual_voltage']:.3f} V")
            self.current_display.config(text=f"{status['actual_current']:.3f} A")
            power = status['actual_voltage'] * status['actual_current']
            self.power_display.config(text=f"{power:.3f} W")

            # Status-Labels aktualisieren
            self.mode_label.config(text=f"Modus: {status['mode']}")
            self.output_status_label.config(text=f"Ausgang: {'EIN' if status['output_on'] else 'AUS'}")
            self.remote_status_label.config(text=f"Remote: {'Ja' if status['remote_mode'] else 'Nein'}")
            self.temp_label.config(text=f"Übertemperatur: {'WARNUNG!' if status['over_temp'] else 'OK'}")

            if status['over_temp']:
                self.temp_label.config(foreground="red")
            else:
                self.temp_label.config(foreground="black")

            # Buttons aktualisieren
            if status['output_on']:
                self.output_btn.config(text="Ausgang AUS")
            else:
                self.output_btn.config(text="Ausgang EIN")

            if status['remote_mode']:
                self.remote_btn.config(text="Remote-Modus AUS")
            else:
                self.remote_btn.config(text="Remote-Modus EIN")

        # Graphen aktualisieren
        if len(self.timestamps) > 0:
            self._update_plots()

    def _update_plots(self):
        """Aktualisiert die Matplotlib-Graphen"""
        times = list(self.timestamps)
        voltages = list(self.voltage_data)
        currents = list(self.current_data)
        powers = list(self.power_data)

        # Spannung/Strom Plot aktualisieren
        self.line_voltage.set_data(times, voltages)
        self.line_current.set_data(times, currents)

        # Leistungs-Plot aktualisieren
        self.line_power.set_data(times, powers)

        # Achsen automatisch skalieren
        if len(times) > 0:
            self.ax1.set_xlim(min(times), max(times))
            self.ax2.set_xlim(min(times), max(times))

            if len(voltages) > 0:
                v_max = max(voltages) if max(voltages) > 0 else 1
                c_max = max(currents) if max(currents) > 0 else 1
                self.ax1.set_ylim(0, max(v_max, c_max) * 1.1)

            if len(powers) > 0:
                p_max = max(powers) if max(powers) > 0 else 1
                self.ax2.set_ylim(0, p_max * 1.1)

        self.canvas.draw_idle()

    def _set_voltage(self):
        """Setzt die Ausgangsspannung"""
        if not self.connected:
            messagebox.showwarning("Warnung", "Nicht verbunden!")
            return

        try:
            voltage = self.voltage_var.get()
            if self.psu.set_voltage(voltage):
                messagebox.showinfo("Erfolg", f"Spannung auf {voltage:.2f}V gesetzt")
            else:
                messagebox.showerror("Fehler", "Spannung konnte nicht gesetzt werden")
        except ValueError as e:
            messagebox.showerror("Fehler", str(e))

    def _set_current(self):
        """Setzt die Strombegrenzung"""
        if not self.connected:
            messagebox.showwarning("Warnung", "Nicht verbunden!")
            return

        try:
            current = self.current_var.get()
            if self.psu.set_current(current):
                messagebox.showinfo("Erfolg", f"Strombegrenzung auf {current:.2f}A gesetzt")
            else:
                messagebox.showerror("Fehler", "Strom konnte nicht gesetzt werden")
        except ValueError as e:
            messagebox.showerror("Fehler", str(e))

    def _toggle_output(self):
        """Schaltet den Ausgang ein/aus"""
        if not self.connected or not hasattr(self, 'last_status'):
            return

        current_state = self.last_status.get('output_on', False)
        new_state = not current_state

        if self.psu.set_output(new_state):
            state_text = "eingeschaltet" if new_state else "ausgeschaltet"
            messagebox.showinfo("Erfolg", f"Ausgang {state_text}")
        else:
            messagebox.showerror("Fehler", "Ausgang konnte nicht geschaltet werden")

    def _toggle_remote(self):
        """Schaltet den Remote-Modus ein/aus"""
        if not self.connected or not hasattr(self, 'last_status'):
            return

        current_state = self.last_status.get('remote_mode', False)
        new_state = not current_state

        if self.psu.set_remote_mode(new_state):
            state_text = "aktiviert" if new_state else "deaktiviert"
            messagebox.showinfo("Erfolg", f"Remote-Modus {state_text}")
        else:
            messagebox.showerror("Fehler", "Remote-Modus konnte nicht geschaltet werden")

    def on_closing(self):
        """Wird beim Schließen des Fensters aufgerufen"""
        if self.connected:
            self._toggle_connection()
        self.root.destroy()


def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = PowerSupplyGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
