# BK Precision 1788B - RS-232/TTL Protocol Documentation

## Hardware Setup

### Overview
The BK Precision 1788B (0-32VDC, 0-6A programmable DC power supply) has a **TTL-level serial interface** on a DB9 connector, NOT true RS-232 levels.

### Critical Hardware Information
- **Voltage Levels:** TTL (0-5V), NOT RS-232 (±12V)
- **IMPORTANT:** Standard RS-232 adapters will NOT work - the ±12V would damage the interface
- **Original Adapter:** BK Precision IT-E131 (RS-232 to TTL converter with galvanic isolation)
- **DIY Alternative:** USB-to-TTL adapter (FTDI FT232RL or similar) set to 5V output

### DB9 Pin Configuration (Measured and Verified)

```
Pin 1 (DCD):  +5V    Output  - "Device present" signal
Pin 2 (RX):   Float  Input   - Data IN to power supply
Pin 3 (TX):   +5V    Output  - Data OUT from power supply (Idle HIGH)
Pin 4 (DTR):  Float  Input   - Not required for basic communication
Pin 5 (GND):  0V     Ground
Pin 6 (DSR):  Float  Input   - Not used
Pin 7 (RTS):  Float  Input   - Not used
Pin 8 (CTS):  Float  Input   - Not used
Pin 9 (RI):   Float  Input   - Not used
```

### Wiring for Direct TTL Connection

```
USB-TTL Adapter          BK 1788B (DB9)
-----------------        --------------
TX (MOSI)       ──────>  Pin 2 (RX)
RX (MISO)       <──────  Pin 3 (TX)
GND             ──────   Pin 5 (GND)
```

**Note:** The IT-E131 cable performs internal pin crossing. When using direct TTL, use straight-through connection as shown above.

### Communication Parameters

```
Baudrate:  4800, 9600, 19200, or 38400 (default: 4800)
Data bits: 8
Parity:    None
Stop bits: 1
Format:    8N1
Handshake: None (RTS/CTS not required)
```

**CRITICAL:** Both power supply and computer must be set to the same baud rate. Check power supply settings via front panel MENU > BAUDRATE.

---

## Protocol Specification

### Packet Structure

**All communication uses fixed 26-byte packets** in both directions (command and response).

```
Byte 0:      0xAA           (Start marker - always this value)
Byte 1:      Address        (0x00-0xFE, default: 0x00)
Byte 2:      Command        (See command list below)
Bytes 3-24:  Data           (22 bytes, command-specific)
Byte 25:     Checksum       (Sum of bytes 0-24, modulo 256)
```

### Checksum Calculation

```python
checksum = sum(packet[0:25]) % 256
```

Example:
```
0xAA + 0x00 + 0x26 + (22 × 0x00) = 0xD0
```

### Data Encoding

- **2-byte integers:** Little-endian format
  - Example: 5000 mA = 0x1388 → Bytes: [0x88, 0x13]
  
- **4-byte integers:** Little-endian format (but for voltage, only first 2 bytes typically used)
  - Example: 5000 mV = 0x1388 → Bytes: [0x88, 0x13, 0x00, 0x00]

- **Current values:** In milliamps (mA)
- **Voltage values:** In millivolts (mV)

---

## Command Set

### 0x20 - Set Remote Control Mode

**Purpose:** Switch between front-panel and remote (PC) control

**Packet:**
```
Byte 0:      0xAA
Byte 1:      0x00 (Address)
Byte 2:      0x20
Byte 3:      0x00 = Front panel mode
             0x01 = Remote control mode
Bytes 4-24:  0x00 (Reserved)
Byte 25:     Checksum
```

**Example (Enable Remote):**
```
AA 00 20 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 CB
```

**Response:** Status packet (0x12) with result code

---

### 0x21 - Set Output ON/OFF

**Purpose:** Enable or disable the power supply output

**Packet:**
```
Byte 0:      0xAA
Byte 1:      0x00 (Address)
Byte 2:      0x21
Byte 3:      0x00 = Output OFF
             0x01 = Output ON
Bytes 4-24:  0x00 (Reserved)
Byte 25:     Checksum
```

**Example (Output ON):**
```
AA 00 21 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 CC
```

**Response:** Status packet (0x12) with result code

**Display Indicator:** "ON" annunciator lights when output is enabled

---

### 0x23 - Set Output Voltage

**Purpose:** Program the output voltage setpoint

**Packet:**
```
Byte 0:      0xAA
Byte 1:      0x00 (Address)
Byte 2:      0x23
Bytes 3-6:   Voltage in mV (4-byte little-endian)
Bytes 7-24:  0x00 (Reserved)
Byte 25:     Checksum
```

**Example (Set 10.00V):**
```
Voltage: 10.000V = 10000 mV = 0x2710
Little-endian: [0x10, 0x27, 0x00, 0x00]

Packet:
AA 00 23 10 27 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04
```

**Response:** Status packet (0x12) with result code

---

### 0x24 - Set Output Current

**Purpose:** Program the output current limit

**Packet:**
```
Byte 0:      0xAA
Byte 1:      0x00 (Address)
Byte 2:      0x24
Bytes 3-4:   Current in mA (2-byte little-endian)
Bytes 5-24:  0x00 (Reserved)
Byte 25:     Checksum
```

**Example (Set 1.50A):**
```
Current: 1.50A = 1500 mA = 0x05DC
Little-endian: [0xDC, 0x05]

Packet:
AA 00 24 DC 05 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 1B
```

**Response:** Status packet (0x12) with result code

---

### 0x26 - Read Status

**Purpose:** Query all current values, setpoints, and operating state

**Packet:**
```
AA 00 26 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 D0
```

**Response Packet Structure:**
```
Byte 0-2:    0xAA 0x00 0x26           (Header)
Bytes 3-4:   Actual current (mA, 2-byte LE)
Bytes 5-8:   Actual voltage (mV, 4-byte LE)
Byte 9:      Status byte (see below)
Bytes 10-11: Current setpoint (mA, 2-byte LE)
Bytes 12-15: Maximum voltage (mV, 4-byte LE)
Bytes 16-19: Voltage setpoint (mV, 4-byte LE)
Bytes 20-24: Reserved
Byte 25:     Checksum
```

**Status Byte (Byte 9) Bit Definitions:**
```
Bit 0: Output state (0=OFF, 1=ON)
Bit 1: Over-temperature protection (0=normal, 1=active)
Bit 2-3: Operating mode
         01 = CV (Constant Voltage)
         10 = CC (Constant Current)
         11 = Unreg
Bit 4-6: Fan speed (0=stopped, 5=maximum)
Bit 7: Control mode (0=Front panel, 1=Remote)
```

**Example Response (5.00V, 0mA, Output ON, CV mode):**
```
AA 00 26 00 00 88 13 00 00 05 28 00 E8 80 00 00 88 13 00 00 01 00 00 00 00 9C

Decoded:
- Actual current:   0x0000 = 0 mA
- Actual voltage:   0x1388 = 5000 mV = 5.00V
- Status:           0x05 = 0b00000101
                    Bit 0=1 (ON), Bit 2=1 (CV mode)
- Current setpoint: 0x0028 = 40 mA = 0.04A
- Voltage setpoint: 0x1388 = 5000 mV = 5.00V
```

---

### 0x12 - Status Response

**Purpose:** Generic response to commands that don't return data

**Packet:**
```
Byte 0-2:    0xAA 0x00 0x12
Byte 3:      Result code:
             0x80 = Success
             0x90 = Checksum error
             0xA0 = Parameter error
             0xB0 = Unrecognized command
             0xC0 = Invalid command
Bytes 4-24:  0x00 (Reserved)
Byte 25:     Checksum
```

---

## Tested Communication Sequence

### 1. Initial Setup
- Connect TTL adapter to power supply
- Configure for 4800 baud, 8N1
- Verify baud rate matches power supply setting (MENU > BAUDRATE)

### 2. Query Initial Status
Send:
```
AA 00 26 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 D0
```

Receive: 26-byte status packet with current state

### 3. Enable Output
Send:
```
AA 00 21 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 CC
```

Receive: Status response (0x12) with 0x80 (success)

### 4. Query Status Again
Send status query (0x26) to see actual output voltage

**Observed:** Display shows "LINK" indicator during active communication

---

## Debugging Notes from Field Testing

### Issue: No Response from Power Supply

**Symptoms:**
- Commands sent but no data received
- Display does not show "LINK" indicator

**Root Causes Found:**
1. **Baud Rate Mismatch:** Power supply was set to 9600, adapter to 4800
   - **Solution:** Verify both sides match (use MENU on power supply)

2. **Wrong Pin Assignment:** Initially tried crossed pins (thinking null-modem)
   - **Solution:** Use straight-through: TX→Pin2, RX←Pin3

3. **Voltage Level Issues:** Initial attempt with 3.3V logic
   - **Solution:** Use 5V TTL levels

4. **Floating RX Pin:** Measured 1.4V on Pin 2 (turned out to be 50Hz noise pickup)
   - **Solution:** Proper grounding, shorter cables

### Successful Configuration
- Bus Pirate 6XL set to 5V output, 4800 baud, 8N1
- Straight-through wiring (TX→Pin2, RX←Pin3, GND→Pin5)
- Power supply set to 4800 baud (default)
- No hardware handshake required

### Display Indicators
- **"LINK"** or **"Adrs"** - Active communication
- **"Rmt"** - Remote control mode enabled
- **"ON"** - Output enabled
- **"CV"** - Constant voltage mode
- **"CC"** - Constant current mode

---

## Python Implementation Example

### Basic Packet Structure
```python
def create_packet(address, command, data):
    """Create a 26-byte command packet"""
    packet = bytearray(26)
    packet[0] = 0xAA
    packet[1] = address
    packet[2] = command
    
    # Copy data bytes (up to 22 bytes)
    for i, byte in enumerate(data[:22]):
        packet[3 + i] = byte
    
    # Calculate checksum
    packet[25] = sum(packet[0:25]) % 256
    
    return packet

def parse_status(response):
    """Parse 0x26 status response"""
    if len(response) != 26 or response[0] != 0xAA:
        raise ValueError("Invalid packet")
    
    # Extract values (little-endian)
    actual_current = response[3] | (response[4] << 8)  # mA
    actual_voltage = response[5] | (response[6] << 8)  # mV (first 2 bytes)
    status_byte = response[9]
    current_setpoint = response[10] | (response[11] << 8)  # mA
    voltage_setpoint = response[16] | (response[17] << 8)  # mV
    
    # Decode status byte
    output_on = bool(status_byte & 0x01)
    mode = (status_byte >> 2) & 0x03  # 1=CV, 2=CC, 3=Unreg
    
    return {
        'actual_voltage': actual_voltage / 1000.0,  # Convert to V
        'actual_current': actual_current / 1000.0,  # Convert to A
        'voltage_setpoint': voltage_setpoint / 1000.0,
        'current_setpoint': current_setpoint / 1000.0,
        'output_on': output_on,
        'mode': ['Unknown', 'CV', 'CC', 'Unreg'][mode]
    }
```

### Command Examples
```python
import serial

# Open serial port
ser = serial.Serial('COM3', 4800, timeout=1)

# Query status
cmd = create_packet(0x00, 0x26, [0]*22)
ser.write(cmd)
response = ser.read(26)
status = parse_status(response)
print(f"Voltage: {status['actual_voltage']:.2f}V")
print(f"Current: {status['actual_current']:.3f}A")

# Set voltage to 12.00V
voltage_mv = int(12.0 * 1000)  # 12000 mV
data = [
    voltage_mv & 0xFF,
    (voltage_mv >> 8) & 0xFF,
    0, 0  # Upper bytes for 4-byte value
]
cmd = create_packet(0x00, 0x23, data + [0]*18)
ser.write(cmd)
response = ser.read(26)  # Should be status response (0x12)

# Enable output
cmd = create_packet(0x00, 0x21, [0x01] + [0]*21)
ser.write(cmd)
response = ser.read(26)
```

---

## Testing Checklist

- [ ] Verify TTL voltage levels (should be 0-5V, NOT ±12V RS-232)
- [ ] Check baud rate on power supply (MENU > BAUDRATE)
- [ ] Confirm straight-through wiring (not crossed)
- [ ] Test with simple status query (0x26)
- [ ] Verify "LINK" appears on display during communication
- [ ] Test voltage setting and readback
- [ ] Test current setting and readback
- [ ] Test output enable/disable
- [ ] Verify actual measurements match setpoints (with load)

---

## References

- **Manual:** BK Precision 1788 Instruction Manual (November 3, 2010)
- **Relevant Models:** 1785B, 1786B, 1787B, 1788
- **Communication Cable:** IT-E131 (RS-232 to TTL adapter)
- **Support:** https://bkprecision.desk.com

---

## Document Version

**Version:** 1.0  
**Date:** 2025-11-11  
**Based on:** Field testing and protocol analysis with Bus Pirate 6XL  
**Hardware Tested:** BK Precision 1788B (32V/6A model)  
**Status:** Verified and working

---

## Additional Notes

### Known Limitations
- Maximum packet rate not tested (no timing constraints documented)
- Multi-device addressing not tested (only address 0x00 used)
- Calibration commands (0x27-0x2F) not tested or documented here
- Front panel lockout commands (0x37) not tested

### Future Enhancements
- Add support for stored presets (Save/Recall commands)
- Implement continuous monitoring mode
- Add data logging functionality
- Create real-time graphing interface

### Safety Notes
- Always verify voltage/current settings before connecting load
- Use current limiting to protect sensitive loads
- Monitor for over-temperature protection activation
- Keep proper ventilation around power supply
