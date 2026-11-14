# 1. Functional requirements

These define what the final product must do.

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| FUN-01 | Measure wind speed | 0.3–20 m/s minimum operating range | Must |
| FUN-02 | Measure wind direction | 0-360°, can be incremented in relatively large forks (10-15°)| Must |
| FUN-03 | Measure ambient temperature | -20°C to +60°C | Must |
| FUN-04 | Record measurements | Store measurements with timestamps and device ID| Must |
| FUN-05 | Data collection interval | Produce measurement records every 10 minutes | Must |
| FUN-06 | Data processing | Calculate wind speed, direction and temperature from sensor readings | Must |
| FUN-07 | Data cleaning | Detect and reject invalid measurements and sensor faults | Must |
| FUN-08 | Calibration | Allow wind speed, direction and temperature measurements to be calibrated | Must |
| FUN-09 | Autonomous operation | Operate without continuous human intervention | Must |
| FUN-10 | Data retrieval | Data must be sent by LoraWan to a central gateway linked to a database | Must |

# 2. Measurement and performance requirements

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| PER-01 | Wind speed accuracy | Maximum error of ±0.3 m/s | Must |
| PER-02 | Wind direction accuracy | Maximum error of ±10° | Must |
| PER-03 | Temperature accuracy | Maximum error of ±0.5°C | Must |
| PER-04 | Wind speed minimum | Detect wind speeds of 0.3 m/s or lower | Must |
| PER-05 | Wind speed maximum | Measure at least 20 m/s | Must |
| PER-06 | Temperature minimum | Operate at -20°C or below | Must |
| PER-07 | Temperature maximum | Operate at +60°C or above | Must |
| PER-08 | Measurement repeatability | Repeated measurements under identical conditions must remain within an established tolerance | Must |
| PER-09 | Measurement resolution | Define sufficiently small increments to support the required accuracy | Must |
| PER-10 | Measurement drift | Accuracy must remain within specification between calibration intervals | Should |
| PER-11 | Wind gust measurement | Record maximum wind speed during each 10-minute interval | Should |

**Clarifications:**

- Distinguish the minimum wind speed that the rotor can physically start at from the minimum speed that can be measured accurately.

# 3. Mechanical requirements

## 3.1 Rotor and cups

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| MEC-01 | Cup configuration | Three-cup rotor | Must |
| MEC-02 | Cup geometry | Defined and optimised for low starting wind speed | Must |
| MEC-03 | Rotor dimensions | Defined through aerodynamic and mechanical design | Must |
| MEC-04 | Rotor balance | Minimise imbalance and vibration | Must |
| MEC-05 | Rotor mass | Minimise mass while maintaining structural rigidity | Should |
| MEC-06 | Rotor inertia | Minimise inertia to improve response time | Must |
| MEC-07 | Maximum rotor speed | Withstand rotational speed corresponding to maximum operating wind speed | Must |
| MEC-08 | Cup attachment | Secure attachment resistant to vibration and wind loading | Must |
| MEC-09 | Cup material | Weather-resistant, UV-resistant and sufficiently rigid | Must |

## 3.2 Shaft and bearings

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| MEC-10 | Shaft material | Corrosion-resistant material | Must |
| MEC-11 | Shaft diameter | Determined by mechanical strength and bearing selection | Must |
| MEC-12 | Shaft alignment | Minimise misalignment and runout | Must |
| MEC-13 | Bearing load | Withstand rotor weight and calculated wind-induced loads | Must |
| MEC-14 | Bearing friction | Minimise starting and running friction | Must |
| MEC-15 | Bearing torque | Remain below the available aerodynamic starting torque at minimum wind speed | Must |
| MEC-16 | Bearing lifetime | Achieve at least six months between planned maintenance operations | Must |
| MEC-17 | Lubrication | Suitable lubricant for the operating temperature range | Must |
| MEC-18 | Bearing replacement | Bearings must be replaceable without replacing the entire assembly | Should |
| MEC-19 | Axial and radial play | Remain within defined mechanical tolerances | Must |
| MEC-20 | Shaft strength | Withstand calculated bending and torsional stresses with an appropriate safety factor | Must |

**Important engineering note:** Bearing load must include radial and axial forces, not just the weight of the rotating assembly. The shaft should also be checked for bending moments caused by wind loading.

# 4. Structural and installation requirements

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| STR-01 | Mounting compatibility | Compatible with the intended urban light-pole installation | Must |
| STR-02 | Installation | Installable using a ladder and standard tools | Must |
| STR-03 | Mounting security | Must remain securely attached to the pole under expected environmental loads | Must |
| STR-04 | Structural strength | Withstand operating wind loads and mechanical stresses | Must |
| STR-05 | Survival wind speed | 25m/s (about 100km/h winds) | Must |
| STR-06 | Maximum dimensions | Compatible with available installation space | Should |
| STR-07 | Maximum weight | Compatible with the mounting structure and safe installation | Should |
| STR-08 | Component accessibility | Internal components must be accessible for maintenance | Must |
| STR-09 | Assembly | Mechanical assembly should use standard fasteners and accessible components | Should |
| STR-10 | Tamper resistance | Prevent unauthorised access to critical components | Must |
| STR-11 | Impact resistance | Withstand foreseeable urban mechanical impacts | Must |

# 5. Electronic requirements

## 5.1 Wind-speed sensing

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| ELE-01 | Rotation detection | Detect rotor rotation using a magnetic sensor | Must |
| ELE-02 | Pulse detection | Reliably detect every magnet passage | Must |
| ELE-03 | Pulse resolution | Sufficient to achieve the required wind-speed resolution | Must |
| ELE-04 | Sensor positioning | Maintain a controlled magnet-to-sensor distance | Must |
| ELE-05 | Signal quality | Prevent false pulses and missed detections | Must |
| ELE-06 | Sensor frequency | Support the maximum expected rotor rotational frequency | Must |
| ELE-07 | Signal processing | Calculate rotational frequency from pulse timing | Must |
| ELE-08 | Calibration | Convert rotational frequency into calibrated wind speed | Must |

## 5.2 Electronics and microcontroller

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| ELE-09 | Microcontroller | Suitable for pulse timing, sensor acquisition and data processing | Must |
| ELE-10 | Timer resolution | Sufficient for accurate pulse-period measurement | Must |
| ELE-11 | Operating voltage | Preferably 3.3v, or 5V | Must |
| ELE-12 | Power consumption | Minimise average consumption to achieve battery autonomy | Must |
| ELE-13 | Electrical protection | Protect against ESD, voltage transients and incorrect connections | Should |
| ELE-14 | Temperature compatibility | Electronics must operate from -20°C to +60°C | Must |
| ELE-15 | Fault detection | Detect sensor disconnection, missing pulses and abnormal readings | Should |
| ELE-16 | Low-battery detection | Provide an indication of insufficient battery voltage | Should |
| ELE-17 | Firmware recovery | Include watchdog or equivalent fault recovery functionality | Should |

## 5.3 Data acquisition and storage

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| ELE-18 | Internal acquisition | Acquire measurements continuously or at a sufficiently high internal rate | Must |
| ELE-19 | Data averaging | Calculate average wind speed over each 10-minute interval | Must |
| ELE-20 | Data storage | Retain measurements locally or transmit them to an external system | Must |
| ELE-21 | Data integrity | Prevent corrupted or incomplete records | Must |
| ELE-22 | Timestamping | Associate each record with its measurement time | Must |
| ELE-23 | Communication | Define a suitable data transmission or retrieval interface | Must |
| ELE-24 | Data loss | Minimise data loss during power or communication interruptions | Should |

# 6. Power and autonomy requirements

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| POW-01 | Power supply | Battery-powered autonomous operation | Must |
| POW-02 | Battery lifetime | At least one year between battery replacements | Must |
| POW-03 | Power consumption | Compatible with the battery capacity and annual autonomy target | Must |
| POW-04 | Battery accessibility | Battery must be replaceable without dismantling the entire device | Must |
| POW-05 | Battery monitoring | Monitor battery voltage or remaining capacity | Should |
| POW-06 | Winter operation | Define whether batteries are disconnected during winter | Must |
| POW-07 | Solar power | Evaluate feasibility, but do not depend on solar charging for the initial prototype | Could |

# 7. Environmental requirements

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| ENV-01 | Waterproofing | Define a minimum IP protection rating; IP65 is a proposed initial target | Must |
| ENV-02 | Dust resistance | Prevent dust from interfering with bearings and electronics | Must |
| ENV-03 | Temperature resistance | Operate from -20°C to +60°C | Must |
| ENV-04 | UV resistance | Materials must withstand prolonged outdoor UV exposure | Must |
| ENV-05 | Corrosion resistance | Resist outdoor atmospheric corrosion | Must |
| ENV-06 | Humidity | Withstand high humidity and condensation | Must |
| ENV-07 | Bird resistance | Prevent nesting, perching and obstruction of moving parts as far as practicable | Must |
| ENV-08 | Vandalism resistance | Resist foreseeable urban tampering and impacts | Must |
| ENV-09 | Ice resistance | Define acceptable operation and survival conditions during icing | Should |
| ENV-10 | Wind resistance | Remain functional at 20 m/s and survive a separately defined higher wind speed | Must |
| ENV-11 | Insect resistance | Prevent insects from entering sensitive internal components | Should |

# 8. Maintenance and lifetime requirements

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| MAI-01 | Maintenance frequency | Two planned maintenance interventions per year | Must |
| MAI-02 | Autumn maintenance | Prepare the system for winter and disconnect batteries if required | Must |
| MAI-03 | Spring maintenance | Inspect bearings, renew lubricant if required and replace batteries according to their service interval | Must |
| MAI-04 | Bearing inspection | Bearings inspected during scheduled maintenance | Must |
| MAI-05 | Lubrication | Lubricant service interval of at least six months, subject to validation | Must |
| MAI-06 | Component accessibility | Components accessible using standard tools | Must |
| MAI-07 | Maintenance time | Define maximum intervention duration | Should |
| MAI-08 | Component replacement | Individual components replaceable without replacing the entire instrument | Should |
| MAI-09 | Calibration | Provide an accessible calibration procedure | Must |
| MAI-10 | Service lifetime | Define a target overall product lifetime, independently of maintenance intervals | Must |

# 9. Calibration and testing requirements

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| TES-01 | Reference instrument | Use an available ultrasonic anemometer as the reference | Should |
| TES-02 | Fan testing | Use a controlled fan setup to compare measurements | Should |
| TES-03 | Wind-speed calibration | Establish the relationship between rotor frequency and reference wind speed | Must |
| TES-04 | Wind-direction calibration | Compare wind-vane output against known angular positions | Must |
| TES-05 | Temperature calibration | Compare temperature readings against a suitable reference thermometer | Must |
| TES-06 | Repeatability testing | Repeat measurements at identical conditions | Must |
| TES-07 | Low-speed testing | Verify the 0.3 m/s requirement | Must |
| TES-08 | High-speed testing | Verify operation at 20 m/s | Must |
| TES-09 | Environmental testing | Validate operation at temperature and humidity extremes where feasible | Should |
| TES-10 | Long-term testing | Monitor drift, wear and measurement stability | Should |

# 10. Economic and product requirements

| ID | Requirement | Target / specification | Priority |
|---|---|---|---|
| ECO-01 | Prototype development budget | Maximum CHF 500 | Must |
| ECO-02 | Target production cost | Maximum CHF 30 per unit | Must |
| ECO-03 | Manufacturing simplicity | Minimise specialised manufacturing processes | Should |
| ECO-04 | Assembly simplicity | Minimise assembly operations and specialised tools | Should |
| ECO-05 | Repairability | Prefer replaceable individual components | Should |
| ECO-06 | Maintenance cost | Minimise recurring maintenance and replacement costs | Should |

**Budget distinction:** CHF 500 covers the development prototype, including testing and possible iterations. CHF 30 is the intended future unit cost and should be assessed separately through a preliminary production bill of materials.
