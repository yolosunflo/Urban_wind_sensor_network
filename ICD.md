# DOCUMENT 4 — INTERFACE CONTROL DOCUMENT (ICD)

**Project:** Urban Wind Sensor Network  
**Version:** 1.0 — Preliminary Hardware Interface Definition  
**Main controller:** Seeed Wio-E5 Mini

## 1. Purpose

This document defines the electrical interfaces between the Wio-E5 Mini, sensors, and power electronics.

The prototype uses:
- A 3.6 V bench power supply.
- A TPS61023 boost converter to generate 5 V.
- A Seeed Wio-E5 Mini for processing and LoRaWAN communication.
- An AS5600 magnetic angle sensor for wind direction.
- An SHT41 temperature sensor.
- A magnetic pickup for wind-speed measurement.

## 2. Microcontroller Pin Mapping

| Wio-E5 Interface | Connected Hardware | Signal Type | Function |
|---|---|---|---|
| D4 (provisional) | Reed switch / Hall sensor | Digital input / Interrupt | Detect anemometer rotor rotation |
| SDA | AS5600 | I²C data | Read wind direction |
| SCL | AS5600 | I²C clock | Read wind direction |
| SDA | SHT41 | I²C data | Read ambient temperature |
| SCL | SHT41 | I²C clock | Read ambient temperature |
| D10 (provisional) | MOSFET gate | Digital output | Control switched 5 V load |
| GND | All electronic components | Ground | Common electrical reference |

**Important:** The AS5600 and SHT41 share the same I²C bus.

Proposed I²C addresses:

| Device | I²C Address |
|---|---|
| AS5600 | 0x36 |
| SHT41 | 0x44 (default) |

The actual GPIO assignments must be verified against the Wio-E5 Mini board pinout before implementation.

## 3. Power Distribution

### 3.1 Power Rails

| Power ID | Source | Destination | Voltage | Function |
|---|---|---|---|---|
| PWR-01 | Bench power supply | Main input | 3.6 V DC | Primary prototype supply |
| PWR-02 | Main input | TPS61023 input | 3.6 V DC | Boost converter input |
| PWR-03 | TPS61023 output | Wio-E5 Mini | 5 V DC | Power MCU and LoRa radio |
| PWR-04 | Regulated logic supply | AS5600 | Compatible supply | Wind-direction sensing |
| PWR-05 | Regulated logic supply | SHT41 | Compatible supply | Temperature sensing |
| PWR-06 | Regulated logic supply | Hall sensor (if selected) | Compatible supply | Rotor detection |
| PWR-07 | TPS61023 output | MOSFET-switched load | 5 V DC | Supply external peripherals |
| PWR-08 | All supply returns | Common ground | 0 V | Electrical reference |

The AS5600 and SHT41 supply voltages must be selected according to their component or breakout-board specifications.

I²C pull-up resistors must connect to a voltage compatible with the Wio-E5 Mini GPIO logic levels.

### 3.2 Power Architecture


flowchart TB
    A["3.6 V DC Bench Supply"] --> B["TPS61023 Boost Converter<br/>3.6 V → 5 V"]
    B --> C["5 V Power Rail"]

    C --> D["Seeed Wio-E5 Mini<br/>MCU + LoRaWAN"]
    C --> E["Sensor Regulation<br/>To be finalized"]

    E --> F["AS5600<br/>Wind Direction"]
    E --> G["SHT41<br/>Temperature"]
    E --> H["Hall / Reed Sensor<br/>Wind Speed"]

    I["Common Ground"] -.-> D
    I -.-> F
    I -.-> G
    I -.-> H

    style A fill:#e8eef7,stroke:#54749a,color:#172b46
    style B fill:#e8eef7,stroke:#54749a,color:#172b46
    style C fill:#dce9f7,stroke:#54749a,color:#172b46
    style D fill:#e2f0e8,stroke:#54846a,color:#183b28
    style E fill:#fff0d9,stroke:#bd9145,color:#553b12
    style F fill:#f3f3f3,stroke:#888,color:#222
    style G fill:#f3f3f3,stroke:#888,color:#222
    style H fill:#f3f3f3,stroke:#888,color:#222
    style I fill:#f3f3f3,stroke:#888,color:#222

*Figure X — Prototype power distribution architecture.
The TPS61023 generates the 5 V rail from the 3.6 V bench supply.
The sensor supply regulation stage remains to be finalized.*

**Power architecture constraints:**

1. The bench supply provides 3.6 V to the TPS61023.
2. The TPS61023 generates the 5 V rail.
3. The 5 V rail powers the Wio-E5 Mini through its specified power input.
4. Sensor supply voltages must respect their respective datasheets.
5. I²C pull-ups must be compatible with the Wio-E5 logic voltage.
6. The boost converter must support peak current during LoRa transmission.
7. All subsystems share a common ground.

## 4. Sensor Interfaces

### 4.1 Anemometer — Wind Speed

| Parameter | Specification |
|---|---|
| Sensor principle | Magnetic pulse detection |
| Mechanical input | Three-cup rotor |
| Electrical output | Digital pulse |
| MCU connection | D4 (provisional) |
| Acquisition method | GPIO interrupt / pulse timing |
| Processed variable | Rotor frequency and wind speed |

The number of magnetic events per revolution must be defined by the mechanical and electronics teams.

### 4.2 Wind Direction — AS5600

| Parameter | Specification |
|---|---|
| Sensor | AS5600 magnetic rotary position sensor |
| Measurement principle | Magnetic angular position detection |
| Mechanical input | Rotating wind vane and associated magnet |
| Electrical interface | I²C |
| MCU connections | SDA and SCL |
| I²C address | 0x36 |
| Resolution | 12-bit angular measurement |
| Processed variable | Wind direction, 0–360° |

**Mechanical integration requirements:**

- A suitable diametrically magnetised magnet must be mounted on the rotating vane assembly.
- The AS5600 must be positioned and aligned with the magnet according to its datasheet.
- The magnet-to-sensor air gap must be defined and maintained.
- The mechanical assembly must permit full 360° rotation.
- The sensor must not experience mechanical contact with the rotating assembly.

**Firmware requirements:**

- Read angular measurements through I²C.
- Convert the sensor output into a wind-direction value.
- Handle the 0°/360° transition correctly.
- Apply an offset calibration to establish the physical north reference.

### 4.3 Temperature — SHT41

| Parameter | Specification |
|---|---|
| Sensor | SHT41 |
| Measurement | Ambient temperature |
| Communication | I²C |
| MCU connections | SDA and SCL |
| Default I²C address | 0x44 |
| Processed variable | Ambient temperature |

The SHT41 shares the I²C bus with the AS5600.

## 5. Power Control Interface

| Parameter | Specification |
|---|---|
| Control signal | D10 (provisional) |
| Control component | Logic-level MOSFET |
| Controlled rail | 5 V |
| Function | Enable / disable selected external load |
| Default state | OFF during reset |

The MOSFET must be selected according to its gate-drive requirements and load current.

## 6. Interface Verification

Before integration, verify:

1. The bench supply delivers a stable 3.6 V.
2. The TPS61023 generates a stable 5 V output.
3. The Wio-E5 Mini operates correctly from the 5 V output.
4. The sensor supply rails have correct voltage levels.
5. The common ground is correctly connected.
6. D4 detects magnetic rotor pulses.
7. The AS5600 is detected over I²C at address 0x36.
8. The SHT41 is detected over I²C at address 0x44.
9. Both sensors operate simultaneously on the same I²C bus.
10. The AS5600 reports correct angular changes when the vane is rotated.
11. The MOSFET correctly switches the intended load.
12. All GPIO and I²C signal voltages are compatible with the Wio-E5 Mini.

## 7. Open Hardware Decisions

| ID | Open Decision | Responsible Team |
|---|---|---|
| ICD-01 | Confirm physical GPIO mapping for D4 and D10 | Electronics |
| ICD-02 | Select reed switch or Hall sensor | Electronics |
| ICD-03 | Determine magnet count and spacing for anemometer | Mechanical + Electronics |
| ICD-04 | Select AS5600 magnet and define mechanical alignment | Mechanical |
| ICD-05 | Define AS5600 magnet-to-sensor air gap | Mechanical |
| ICD-06 | Confirm I²C pull-ups and bus voltage | Electronics |
| ICD-07 | Finalise sensor supply voltage architecture | Electronics |
| ICD-08 | Confirm TPS61023 output and peak-current capability | Electronics |
| ICD-09 | Select MOSFET and gate-drive configuration | Electronics |
| ICD-10 | Confirm connectors and wiring | Integration |

