# TODO — BK1788-Python

## Offen

- [ ] **Kalibrier-Sequenz implementieren** (`0x27`–`0x2F`, `0x32`)
  - Aus dem offiziellen Instruction Manual (`BK1788_Instruction_Manual.pdf`, Abschnitt Protokoll/Kalibrierung) ins `bk1788b.py` einbauen.
  - Befehle laut Manual:
    - `0x27` — Enter calibration mode (mit Passwort: Byte 5 = `0x28`, Byte 6 = `0x01`)
    - `0x28` — Read calibration mode state
    - `0x29` — Calibrate voltage value (3 Punkte sequenziell, Punkt 1–3)
    - `0x2A` — Send actual output voltage to calibration program
    - `0x2B` — Calibrate current value (Punkt 1–2)
    - `0x2C` — Send actual output current to calibration program
    - `0x2D` — Save calibration data to EEPROM
    - `0x2E` — Set calibration information (ASCII, Byte 4–23)
    - `0x2F` — Read calibration information
    - `0x32` — **Restore factory default calibration data** (interessant für den CC-Defekt)
  - Hinweis: Im Kalibriermodus sind Output-Änderungen gesperrt; Cal-Protection ggf. erst auf OFF setzen.
  - Motivation: Netzteil hängt im Constant-Current-Mode / liefert keine Spannung — prüfen, ob Cal-Reset (`0x32`) statt Hardware-Defekt hilft.

## Hardware-Defekt — GELÖST (2026-06-29)
- **Ursache gefunden:** Reverse-Schutzdiode **1D24 (1N5408)** durchlegiert (sichtbarer Längsriss im Gehäuse) → Ausgang auf 0 V geklemmt → festes CC.
- **Fix:** ersetzt durch **1N5404** (3 A/400 V, hier 1:1 ausreichend — Diode sieht nur ~32 V in Sperrrichtung). Funktionstest ok, Gerät wieder voll funktionsfähig.
- Pass-Bank (TIP35C/TIP41C), Strommess-Kette und Cal-EEPROM **unbeschädigt** → kein `0x32`-Cal-Reset nötig gewesen.
- Optional: bei Gelegenheit auf robustere 6 A-Type (z. B. 6A10) gegen künftige Akku-Rückspeisung.

### Historie / Referenzen
- Symptom war: bleibt in CC, keine Ausgangsspannung (nach Anschluss eines großen Akkus → Rückspeisung durch 1D24).
- Mainboard ist rebadged **ITECH IT6830-Main-V4.1** (laut EEVblog-Repair-Thread).
- AC-Netzsicherung 1788: 3.15A T 250V (220VAC) / 6.3A T 250V (110VAC) — war nicht die Ursache.
- Schaltplan: `BK1788_Schematic_1785B-1788.pdf`; Mess-/Diagnoseplan in `REPARATUR_MESSPLAN.md`.
