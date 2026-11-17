# DOCUMENT 1 — PROTOTYPE REQUIREMENTS DOCUMENT (PRD)

**Project:** Urban Wind Sensor Network  
**Version:** 1.1 — Proof of Concept (aligned with firmware and server implementation)  
**System configuration:** 2 sensor nodes + 1 LoRaWAN gateway

## 1. Purpose and Scope

This document defines the functional, performance, mechanical, electronic, and integration requirements for the Urban Wind Sensor Network prototype.

The objective is to demonstrate that independently operating sensor nodes can measure wind speed, wind direction, and ambient temperature, calculate one summary per 10-minute window, and transmit it over LoRaWAN to a gateway and a server that checks, stores and displays the data.

The prototype is intended to demonstrate technical feasibility, not production readiness.

### 1.1 System Architecture

Each sensor node consists of:

- Custom three-cup anemometer for wind-speed measurement (magnet + reed switch, one pulse per magnet passage).
- Custom wind vane with AS5600 magnetic angular decoder for wind-direction measurement.
- SparkFun SEN-13314 (TI TMP102) temperature sensor.
- Seeed LoRa-E5 mini (STM32WLE5JC, LoRaWAN built in).
- TPS61023 boost converter (3.6 V → 5 V).
- Battery voltage monitor (resistor divider read by the ADC).
- External bench power supply during prototype testing.

The network chain is: nodes → LoRaWAN gateway → The Things Network (TTN) → MQTT → Python server (decoding, validation, storage, analysis, dashboard).

### 1.2 Node Timing (reference for all documents)

All timing values are defined once, in `firmware/include/config.h`, and must not be retyped elsewhere.

| Parameter | Value | Config name |
|---|---|---|
| Reporting window | 600 s (10 min) | `WINDOW_S` |
| Sampling burst inside the window | 300 s (5 min) | `BURST_S` |
| Sampling rate | 1 Hz (300 samples per burst) | `SAMPLE_PERIOD_MS` |
| Temperature reading | every 10th sample | `TEMP_SAMPLE_EVERY_N` |
| Processing + uplink + receive windows | about 2 s of activity | — |
| Deep sleep | remainder of the window | — |

One window = 5 min sampling → processing and uplink → calibration downlink (if any) received in the receive windows that follow the uplink → deep sleep until the next window. `window_s` in `server/uwsn/config.py` must equal `WINDOW_S`.

### 1.3 Prototype Constraints

- A bench power supply replaces the battery during initial prototype testing.
- The battery is not integrated yet: the power analysis (estimate, then 24-hour measurement) comes first and will drive the battery choice.
- Initial power consumption calculations are estimates only; actual consumption will be measured independently during testing.
- The node has no real-time clock: timestamps are assigned by the network/server when a packet is received.
- Long-term environmental durability and lifetime are outside the PoC verification scope.

## 2. Functional Requirements

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| FUN-01 | Wind-speed measurement | Measure wind speeds from 0.3 to 20 m/s | Must |
| FUN-02 | Wind-direction measurement | Measure direction over 0–360° | Must |
| FUN-03 | Temperature measurement | Measure ambient temperature | Must |
| FUN-04 | Measurement records | Associate each record with a node ID (from the LoRaWAN device) and a timestamp (assigned on reception by the network/server) | Must |
| FUN-05 | Measurement interval | Generate one measurement record every 10 minutes | Must |
| FUN-06 | Data processing | Calculate wind-speed average, wind-direction representation, and temperature | Must |
| FUN-07 | Data transmission | Transmit measurement records using LoRaWAN | Must |
| FUN-08 | Gateway reception | Receive data from all sensor nodes | Must |
| FUN-09 | Data identification | Distinguish measurements originating from each node | Must |
| FUN-10 | Autonomous operation | Execute measurement and transmission cycles without continuous human intervention | Must |

## 3. Measurement and Performance Requirements

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| PER-01 | Wind-speed accuracy | ±(0.3 + 3% of reading) m/s | Must |
| PER-02 | Wind-speed range | 0.3–20 m/s | Must |
| PER-03 | Wind-direction accuracy | ±10° | Must |
| PER-04 | Wind-direction range | 0–360° | Must |
| PER-05 | Temperature accuracy | ±0.5°C against a reference sensor (a temperature offset can be applied by calibration downlink) | Must |
| PER-06 | Measurement resolution | Wind speed: 0.2 m/s; direction: 5°; temperature: 0.5°C | Target |
| PER-07 | Measurement repeatability | Repeat measurements under identical conditions with no more than 5% variation for wind speed | Target |
| PER-08 | Measurement aggregation | Calculate average wind speed and temperature over the 5-minute sampling burst (300 samples at 1 Hz) of each 10-minute window | Must |
| PER-09 | Wind gust measurement | Record maximum wind speed within each window. *TBC: the payload currently carries the mean and the standard deviation; confirm whether the maximum is included* | Should |
| PER-10 | Data validity | Flag missing, invalid, or physically implausible readings (on-node quality flags for too few good samples and sensor faults; plausibility limits; server-side validation) | Must |

**Clarification (aggregation window):** the 10-minute record summarises the 5-minute burst, not the full 10 minutes. Wind during the 5-minute sleep period is not measured. This is a deliberate power-saving choice (`BURST_S ≤ WINDOW_S`).

**Clarification (minimum speed):** the minimum wind speed of 0.3 m/s represents the required measurement threshold. The rotor must also physically start rotating at or under this wind speed. These are related but separate verification criteria.

For wind direction, angular calculations and averaging must account for the 0°/360° boundary. A simple arithmetic average of angles is not acceptable.

## 4. Mechanical Requirements (TO DEFINE)

### 4.1 Rotor and Cups

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| MEC-01 | Rotor configuration | Three-cup rotor | Must |
| MEC-02 | Rotor geometry | Defined through aerodynamic and mechanical calculations | Must |
| MEC-03 | Rotor balance | Minimise imbalance and vibration | Must |
| MEC-04 | Rotor inertia | Minimise inertia to facilitate low-speed starting | Must |
| MEC-05 | Cup attachment | Mechanically secure under prototype operating conditions | Must |
| MEC-06 | Maximum rotational speed | Mechanically withstand operation corresponding to 20 m/s wind speed | Must |
| MEC-07 | Rotor alignment | Maintain alignment with the shaft | Must |

### 4.2 Shaft and Bearings (TO DEFINE)

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| MEC-08 | Shaft design | Defined based on rotor geometry, loads, and bearing selection | Must |
| MEC-09 | Shaft alignment | Minimise misalignment and runout | Must |
| MEC-10 | Bearing selection | Support rotor weight and expected mechanical loads | Must |
| MEC-11 | Bearing friction | Minimise starting and running friction | Must |
| MEC-12 | Bearing starting torque | Remain below available aerodynamic starting torque at 0.3 m/s | Must |
| MEC-13 | Shaft strength | Withstand calculated bending and torsional stresses | Must |
| MEC-14 | Mechanical stability | Avoid excessive vibration or binding during rotation | Must |

### 4.3 Mechanical Design Inputs

The mechanical team must calculate and document the following parameters before finalising the anemometer assembly.

| Parameter | Required Engineering Input |
|---|---|
| Cup diameter | Selected based on aerodynamic performance and available space |
| Cup profile | Shape and geometry of the three cups |
| Rotor radius | Distance between the shaft axis and cup centres |
| Cup spacing | Angular separation and positioning of the cups |
| Rotor mass | Total rotating assembly mass |
| Rotor moment of inertia | Calculated around the shaft axis |
| Shaft diameter | Based on bending, torsion, and bearing constraints |
| Bearing type | Selected based on load capacity and starting friction |
| Bearing starting torque | Maximum allowable torque at the bearing assembly |
| Bearing running torque | Expected friction during normal operation |
| Aerodynamic torque | Estimated available starting torque at 0.3 m/s |
| Maximum rotational speed | Estimated rotor speed at 20 m/s |
| Magnet positioning | Magnet-to-sensor distance and number of magnetic events per revolution (pulse rate at 20 m/s must stay below the 500 Hz debounce limit, `REED_DEBOUNCE_US`) |

**Critical design criterion:**

$$
T_{\text{bearing,start}} < T_{\text{aerodynamic}}(0.3\text{ m/s})
$$

The design must include an appropriate engineering margin. The mechanical team must determine the available aerodynamic torque using the selected rotor geometry and verify the bearing starting torque experimentally.

The rotor must demonstrate repeatable starting at 0.3 m/s under the defined test conditions.

## 5. Electronic Requirements

### 5.1 Wind-Speed Acquisition

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| ELE-01 | Rotation detection | Detect rotor rotation using a magnetic pickup (reed switch) | Must |
| ELE-02 | Pulse detection | Detect each magnet passage reliably (interrupt + debounce) | Must |
| ELE-03 | Signal processing | Calculate rotor rotational frequency from pulse timing | Must |
| ELE-04 | Wind-speed conversion | Convert rotational frequency into calibrated wind speed (gain and offset, adjustable by downlink) | Must |
| ELE-05 | Signal integrity | Avoid false pulses and missed detections | Must |

### 5.2 Wind-Direction Acquisition

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| ELE-06 | Direction sensor | Use an AS5600 magnetic angular decoder to measure a magnet mechanically connected to the wind vane | Must |
| ELE-07 | Data acquisition | Read the AS5600 over I²C | Must |
| ELE-08 | Direction calibration | Establish the relationship between the received value and physical north (direction offset, adjustable by downlink) | Must |

### 5.3 Temperature and Processing Electronics

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| ELE-09 | Temperature sensor | Use a TMP102-based sensor (SparkFun SEN-13314) over I²C | Must |
| ELE-10 | Microcontroller | Use the Seeed LoRa-E5 mini | Must |
| ELE-11 | Power conversion | Use the TPS61023 boost converter (3.6 V → 5 V) | Must |
| ELE-12 | Data acquisition | Acquire sensor measurements and process them locally | Must |
| ELE-13 | Low-power operation | Deep sleep between sampling bursts and uplinks | Must |
| ELE-14 | Fault detection | Detect missing pulses, disconnected sensors, stuck vane or cups, and invalid readings | Should |

## 6. Data and Communication Requirements

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| COM-01 | Communication protocol | LoRaWAN | Must |
| COM-02 | Network topology | Prototype nodes communicating with one gateway | Must |
| COM-03 | Transmission interval | One data transmission per node every 10 minutes | Must |
| COM-04 | Data content | 14-byte uplink: payload version, mean wind speed, wind speed standard deviation, wind direction, temperature, battery voltage, quality flags. Node ID and timestamp come from the network metadata | Must |
| COM-05 | Data reception | Gateway must receive and identify packets from all nodes | Must |
| COM-06 | Packet integrity | Received data must be correctly decoded and associated with its originating node | Must |
| COM-07 | Remote calibration | Calibration values (speed gain/offset, direction offset, temperature offset) can be sent by downlink (9 bytes, port 2), are applied at once and kept in flash | Should |

Payload and downlink formats are documented in `docs/code_documentation.md`.

## 7. Power Requirements

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| POW-01 | Prototype power source | External bench power supply | Must |
| POW-02 | Input voltage | Nominal 3.6 V DC bench-supply rail for the prototype power architecture | Design target |
| POW-03 | Power estimation | Establish an initial estimated average-current budget | Must |
| POW-04 | Power measurement | Measure actual average current independently during testing | Must |
| POW-05 | Operating modes | Characterise burst-sampling, sleep, and LoRa transmission consumption | Must |
| POW-06 | Power stability | Maintain stable supply voltages during sensor operation and radio transmission | Must |
| POW-07 | Battery monitoring | Measure the supply voltage and flag a low battery (below 3.3 V) | Should |

The final battery selection and battery-autonomy validation are explicitly excluded from the prototype requirements.

## 8. Prototype Integration and Environmental Requirements

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| INT-01 | Node integration | Integrate mechanical sensors and electronics into two functional nodes | Must |
| INT-02 | Gateway integration | Connect the gateway to the LoRaWAN network and demonstrate packet reception | Must |
| INT-03 | Outdoor deployment | Deploy the nodes outdoors for a field demonstration | Must |
| INT-04 | Measurement continuity | Demonstrate repeated 10-minute measurement and transmission cycles | Must |
| INT-05 | Mechanical operation | Demonstrate stable rotor and vane movement during testing | Must |
| INT-06 | Prototype protection | Protect electronics sufficiently for the planned outdoor demonstration | Must |

Full IP65 certification, UV endurance, long-term corrosion resistance, vandalism resistance, and survival-wind qualification are not required for this PoC but should be underlined for the final product.

## 9. Server Requirements (software)

| ID | Requirement | Target / Specification | Priority |
|---|---|---|---|
| SRV-01 | Ingestion and decoding | Receive uplinks from TTN (MQTT) and decode the payload | Must |
| SRV-02 | Validation and storage | Validate each record and store it (SQLite) per node | Must |
| SRV-03 | Display and export | Dashboard and CSV export of the stored data | Should |
| SRV-04 | Calibration management | Detect drift against a reference and send new calibration values by downlink | Should |

## 10. Prototype Acceptance Criteria

The prototype will be considered successful when:

1. All sensor nodes operate independently.
2. The custom anemometer demonstrates starting at 0.3 m/s under the defined test conditions.
3. Wind-speed measurements satisfy the specified accuracy over the verified calibration range.
4. Wind direction is measured over 0–360° with a target accuracy of ±10°.
5. Temperature measurements satisfy the ±0.5°C target under the tested ambient conditions.
6. Each node generates and transmits a measurement record every 10 minutes.
7. The gateway receives and correctly identifies packets from all nodes.
8. The average current consumption is measured over a continuous 24-hour period.
9. Outdoor deployment demonstrates meaningful and consistent measurement trends.

Any performance range not physically accessible with the available calibration equipment must be **explicitly documented as not verified** rather than assumed to pass.

## 11. Future Production Goals (Not Prototype Requirements)

The following objectives are acknowledged for future development but are not binding requirements for the three-week prototype.

| Category | Future Production Goal |
|---|---|
| Battery autonomy | At least one year of operation between battery replacements |
| Mechanical lifetime | Target service lifetime of at least three years |
| Maintenance | Two planned maintenance interventions per year |
| Bearing maintenance | Bearing inspection and lubrication at defined intervals |
| Maintenance time | Less than 10 minutes per node |
| Component replacement | Individual components replaceable without replacing the entire instrument |
| Environmental protection | IP65 protection and long-term resistance to humidity, UV exposure, and corrosion |
| Bird resistance | Reduce nesting and obstruction of moving parts |
| Wind survival | Survive a separately defined wind speed above the operating range |
| Manufacturing cost | Target production cost of CHF 30 per node |
| Manufacturing simplicity | Minimise specialised processes and assembly operations |

These objectives will be revisited during the transition from PoC to product development.
