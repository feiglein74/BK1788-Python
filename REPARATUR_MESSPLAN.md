# Reparatur-/Messplan BK1788B — „hängt in CC, 0 V Ausgang"

Abgeleitet aus `BK1788_Schematic_1785B-1788.pdf` (Seite 1 = Analog-/Leistungsteil, Doc IT-001-007-S01).
Symptom: Gerät bleibt im Constant-Current-Mode, keine Ausgangsspannung — aufgetreten nach Rückspeisung eines großen Akkus.

---

## 0. Sicherheit & Vorbereitung

- Netzteil ist **netzbetrieben**: Primärseite 110/220 VAC. Sekundär 42 V, ±12 V, **−30 V**, Ausgangs-Elko **1C15 = 1000 µF/100 V**.
- Vor jedem passiven Test (Abschnitt 2): Netz trennen, **1C15 entladen** (Widerstand ~100 Ω/5 W über die Ausgangsklemmen, mit DMM auf <1 V prüfen).
- Powered-Tests (Abschnitt 1, 3): nur Spannungen messen, GND-Klemme fest, keine Brücken.
- Referenz-Masse für alle Messungen: **AGND** (Analog-GND) am Inter-Board-Stecker, NICHT das Ausgangs-Minus.

## Bauteile physisch identifizieren

- **Analogboard:** Bestückungsdruck-Präfix **„1"** → `1Q1`, `1D24`, `1R28`, `1IC1` usw.
- **Digitalboard:** MCU `U101` (MSP430F135, großes QFP), Cal-EEPROM `U102` (24LC02B, 8-Pin SOIC neben der MCU).
- **Golden Test Point = Inter-Board-Stecker** `1Z1` (Analog) ↔ `J102` (Digital), 12×2. Hier laufen ALLE kritischen Analogsignale UND die DAC-Sollwerte durch — gut messbar ohne SMD-Gefummel.

### Pinbelegung Inter-Board-Stecker (J102 / 1Z1)

| Signal | Funktion | Erwartung |
|---|---|---|
| −30V | Negativversorgung Op-Amps | ≈ −30 V |
| +5V | Logik/Analog | ≈ +5 V |
| AGND / DGND | Massen | 0 V |
| **VOLTAGE_DAC** | Spannungs-Sollwert MCU→Analog | proportional zum eingestellten U |
| **CURRENT_DAC** | Strom-Sollwert MCU→Analog | proportional zum eingestellten I |
| **VOLTAGE_ADC** | Spannungs-Istwert Analog→MCU | proportional zu Vout |
| **CURRENT_ADC** | Strom-Istwert Analog→MCU | ≈ 0 bei Leerlauf |
| VOLT_ADC_HORL | Bereichs-/Sense-Signal | — |
| FAN_CTL, PULSE, TXD, RXD, E1–E7 | Lüfter, Limit-Puls, UART, Extend | — |

---

## 1. Versorgungsspannungen prüfen (Gerät EIN, Leerlauf)

Wenn eine Rail fehlt, regelt nichts → zuerst ausschließen.

| Testpunkt | Soll | Quelle |
|---|---|---|
| +5V | +5.0 V | LM7805 = `1U1` |
| +12V | +12 V | Sek.-Wicklung 14 V |
| −12V | −12 V | LM7912 = `1U3` |
| −30V | ≈ −30 V | 32 V-Wicklung → `1R2` 750R/2W → Zener `1D22` 1N4751A (30 V) |
| +3.3V (Digital) | +3.3 V | REF3033 `U104` |

**→ Fehlt −12 V oder −30 V**, können die TL084 nicht nach unten aussteuern → Pass-Bank bekommt keinen Strom → 0 V. Das ist ein eigenständiger, plausibler Fehler nach Rückspeisung.

---

## 2. Passiv-Test (Gerät AUS, Caps entladen, DMM Dioden-/Ω-Modus)

Reihenfolge = Verdachtswahrscheinlichkeit nach Akku-Rückspeisung:

1. **1D24 (1N5408) Reverse-Schutzdiode über dem Ausgang** — Verdacht #1.
   - In-Circuit Dioden-Modus: eine Richtung ~0.5–0.7 V, andere offen. **Beidseitig ~0 V = durchlegiert** → klemmt Ausgang auf 0 V, Schleife meldet Überstrom → festes CC. Bei Verdacht auslöten und einzeln messen.

2. **Pass-Transistoren** `1Q1`,`1Q5` (TIP35C), `1Q2`,`1Q4` (TIP41C), Treiber `1Q3` (TIP42C).
   - C-E auf Kurzschluss (0 Ω = defekt), B-E / B-C als Dioden plausibel. Emitter-Ballast 0.4R/5W & 0.1R/2W auf Durchgang (nicht hochohmig/abgebrannt).

3. **Brückengleichrichter** `1D15` (KBU8D) — 4× Dioden-Test, kein Kurzschluss.

4. **Strommess-/Clamp-Zweig:** Clamp-Zener `1D20`/`1D21` (1N4735A 6.2 V) an den Op-Amp-Eingängen auf Kurzschluss; Shunt auf Durchgang.

5. **Ausgangsrelais** `1JD1` (OUAZ-SH-112L): Spulendurchgang, Kontakt schaltet hörbar bei Output-ON.

---

## 3. Regelschleife im Betrieb messen — die entscheidende Diagnose (Gerät EIN)

Ziel: Entscheiden, ob der Fehler **digital/Kalibrierung (Software-fixbar)** oder **analog/Hardware** ist.
Vorgehen: in der GUI Output aktivieren, U=z. B. 5 V, I=z. B. 2 A setzen, dann am Stecker messen.

### Entscheidungsbaum

```
CURRENT_DAC messen (Strom-Sollwert MCU→Analog):
│
├─ ≈ 0 V obwohl I=2A gesetzt
│     → Strom-Limit = 0 A → 0 V Ausgang in CC
│     → DIGITAL/KALIBRIERUNG. EEPROM-Cal korrupt.
│     → 0x32 Werks-Cal-Reset versuchen (nicht-invasiv, siehe todo.md). SOFTWARE-FIX.
│
└─ proportional/korrekt (steigt mit Sollwert)
      │
      ├─ CURRENT_ADC HOCH bei Leerlauf (sollte ≈0 sein)
      │     → falsche Überstrom-Meldung → IC2A/Shunt/Clamp defekt
      │     → ANALOG-HARDWARE (Rückspeisungs-Schaden).
      │
      └─ CURRENT_ADC ≈ 0 (korrekt), VOLTAGE_DAC steigt mit Sollwert,
         aber Vout bleibt 0
            → VOLTAGE_ADC prüfen: 0? → Pass-Bank treibt nicht
              → 1D24-Kurzschluss / Pass-Transistor / −12V/−30V-Rail.
```

### Konkret zu messen (AGND als Bezug)

| Signal | Sollwert-Test | Interpretation |
|---|---|---|
| **CURRENT_DAC** | I-Sollwert in 0/1/3/6 A ändern → muss linear steigen | bleibt 0 → DAC/Cal/Stecker-Pin tot → **0x32-Reset zuerst** |
| **VOLTAGE_DAC** | U-Sollwert 0/5/15/30 V ändern → muss linear steigen | bleibt 0 → MCU-Pfad / Cal |
| **CURRENT_ADC** | Leerlauf (keine Last) | sollte ≈0; hoch → Strommessung defekt → IC2A |
| **VOLTAGE_ADC** | mit Output ON | folgt Vout; bei 0 V trotz DAC ok → Pass-Bank |

> Skalierung der DAC-Linien ist gefiltertes PWM aus dem MSP430 (Ref ~3.3 V). Absolutwert ist sekundär — entscheidend ist: **ändert sich der Pegel proportional zum Software-Sollwert?** Wenn nein an CURRENT_DAC → Software-/Cal-Pfad. Wenn ja → analoge Schleife abwärts verfolgen.

---

## 4. Empfohlene Reihenfolge

1. **Abschnitt 1** — Rails ok? (5 min, risikoarm)
2. **Abschnitt 3 / CURRENT_DAC** — ändert sich der Strom-Sollwert mit der Software?
   - **Nein** → `0x32`-Cal-Reset implementieren & probieren (kein Löten). → siehe `todo.md`.
   - **Ja** → **Abschnitt 2** passiv: 1D24, Pass-Bank, Strommess-Zweig.
3. Befund in `hardware-fault-cc-stuck` (Memory) / `todo.md` festhalten.
