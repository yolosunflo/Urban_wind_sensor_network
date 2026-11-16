# DOCUMENT 2 — VERIFICATION AND TEST PLAN

**Project:** Urban Wind Sensor Network  
**Version:** 1.0 — Proof of Concept  
**Test configuration:** 2 sensor nodes + 1 LoRaWAN gateway

## 1. Purpose

This document defines the tests required to verify the Prototype Requirements Document (PRD).

Testing is focused on demonstrating technical feasibility within the three-week development period.

Each test must produce measurable results and supporting evidence.

## 2. Test Equipment

| Equipment | Purpose |
|---|---|
| Bench power supply | Provide stable 3.6 V input power |
| Current logger / data logger | Record current consumption over time |
| Digital multimeter | Verify voltage and current measurements |
| Controlled fan | Generate airflow for anemometer calibration |
| Reference anemometer | Provide reference wind-speed measurements |
| Marked turntable | Provide known wind-vane angular positions |
| Reference thermometer | Validate temperature measurements |
| LoRaWAN gateway | Receive packets from all nodes |
| Computer | Record measurements, inspect packets, and analyse results |
| Stopwatch / timestamped logger | Verify measurement and transmission intervals |

## 3. Test Sequence

Testing will follow this order:

1. Mechanical inspection and starting-torque verification.
2. Individual sensor calibration.
3. Electronic and firmware verification.
4. Power consumption measurement.
5. LoRaWAN communication verification.
6. Outdoor field deployment.
7. Final acceptance review.

---

## 4. Test Procedures

### TEST-01: Mechanical Starting Torque and Rotor Operation

**Related requirements:** MEC-01 to MEC-14, PER-02.

**Objective:** Verify that the custom three-cup rotor can start at the minimum required wind speed.

**Procedure:**

1. Assemble the rotor, shaft, bearings, and magnetic pickup.
2. Check rotor alignment and verify that there is no mechanical binding.
3. Measure the starting torque of the bearing and shaft assembly using a suitable torque measurement method.
4. Record the rotor geometry, mass, and bearing configuration.
5. Position the anemometer in front of a controlled fan.
6. Measure the airflow using a reference anemometer.
7. Increase airflow gradually until the rotor starts rotating.
8. Repeat the test at least five times.
9. Record the starting wind speed for each trial.
10. Verify magnetic pulse detection during rotation.

**Pass criteria:**

- The rotor starts at 0.3 m/s under the defined test conditions.
- Bearing starting torque is lower than the calculated aerodynamic starting torque.
- No mechanical binding or significant instability is observed.
- Magnetic rotation detection operates reliably.

**Evidence:** Starting-torque measurements, rotor geometry, photographs, and starting-speed results.

### TEST-02: Wind-Speed Calibration

**Related requirements:** PER-01, PER-02, PER-06, ELE-01 to ELE-05.

**Objective:** Establish the relationship between rotor pulse frequency and wind speed.

**Procedure:**

1. Position the custom anemometer in front of a controlled fan.
2. Position the reference anemometer close to the custom instrument, ensuring comparable airflow exposure.
3. Allow airflow to stabilise.
4. Test several airflow levels across the available range.
5. Record the reference wind speed and the custom sensor's pulse frequency.
6. Repeat measurements at each airflow level.
7. Calculate the rotor calibration coefficient.
8. Implement the calibration relationship in the firmware.
9. Repeat the measurements using the calibrated firmware.
10. Compare measured and reference wind speeds.

**Accuracy criterion:**

\[
|V_{\text{measured}}-V_{\text{reference}}|
\leq 0.3+0.03V_{\text{reference}}
\]

where wind speed is expressed in m/s.

**Pass criteria:**

- Wind-speed accuracy satisfies the equation over the verified calibration range.
- The rotor detects airflow at 0.3 m/s.
- No significant missed or false magnetic pulses occur.

The full 0.3–20 m/s range must be tested if the available equipment permits. Any untested section must be identified in the final report.

### TEST-03: Wind-Direction Calibration

**Related requirements:** PER-03, PER-04, ELE-06 to ELE-09.

**Objective:** Verify the data reception for the wind-vane angle.

**Procedure:**

1. Mount the wind vane on a marked turntable.
2. Define and mark the 0° reference position.
3. Rotate the turntable through the full 360° range.
4. Record the potentiometer ADC value at regular angular intervals.
5. Include measurements around the 0°/360° boundary.
6. Establish the ADC-to-angle calibration relationship.
7. Implement the conversion in firmware.
8. Repeat measurements at known angular positions.
9. Compare the calculated direction against the turntable reference.

**Pass criteria:**

- The complete 0–360° range is represented correctly.
- Angular error does not exceed ±10°.
- The system handles the 0°/360° transition correctly.
- No discontinuities or ambiguous direction readings occur.

### TEST-04: Temperature Sensor Calibration

**Related requirements:** PER-05, ELE-10.

**Objective:** Validate ambient-temperature measurement accuracy.

**Procedure:**

1. Connect the SHT41 to the Wio-E5 Mini.
2. Place the SHT41 and reference thermometer in the same environment.
3. Allow both sensors to stabilise.
4. Record simultaneous temperature readings.
5. Repeat at several available ambient temperatures.
6. Calculate the difference between the two measurements.

**Pass criterion:**

\[
|T_{\text{measured}}-T_{\text{reference}}|
\leq 0.5^\circ C
\]

The test validates accuracy under the actual conditions available during the PoC. It does not certify the complete production temperature range.

### TEST-05: Data Processing and Aggregation

**Related requirements:** FUN-04 to FUN-06, PER-08, PER-09, PER-10.

**Objective:** Verify that measurements are correctly processed into 10-minute records.

**Procedure:**

1. Run the node continuously.
2. Record raw sensor readings during the test interval.
3. Verify that timestamps are generated. 
4. Verify average wind speed and temperature calculations.
5. Verify wind-direction averaging using circular statistics.
6. Verify maximum wind speed recording if implemented.
7. Introduce a missing or invalid sensor reading.
8. Verify that the firmware identifies and flags invalid data.

**Pass criteria:**

- One valid measurement record is generated every 10 minutes.
- Aggregated values correspond to the raw measurements.
- Each record contains a valid node identifier and timestamp.
- Invalid readings are identified appropriately.

### TEST-06: LoRaWAN Communication

**Related requirements:** COM-01 to COM-06, FUN-07 to FUN-09.

**Objective:** Verify communication between all nodes and the gateway.

**Procedure:**

1. Configure the LoRaWAN gateway.
2. Register and configure the three sensor nodes.
3. Assign each node a unique identifier.
4. Start all nodes.
5. Verify that each node transmits one packet every 10 minutes.
6. Record packets received by the gateway.
7. Compare expected transmissions against received packets.
8. Check the decoded payload and node identifier.
9. Repeat with all three nodes transmitting concurrently.

**Pass criteria:**

- All nodes communicate with the gateway.
- Packets are correctly decoded and associated with their originating node.
- At least 95% of expected packets are received during the field communication test.

Packet success rate:

\[
P_{\text{success}}=
\frac{N_{\text{received}}}{N_{\text{transmitted}}}
\times100
\]

The denominator must count actual transmission attempts, not merely scheduled transmission events.

### TEST-07: Power Measurement Test

**Related requirements:** POW-01 to POW-06.

**Objective:** Measure actual average current consumption using the bench power supply.

**Equipment:**

- Bench power supply set to 3.6 V.
- Current logger capable of recording current over 24 hours.
- Digital multimeter.
- Complete sensor node.

**Procedure:**

1. Connect the bench power supply to the node's 3.6 V input.
2. Verify the supply voltage using a multimeter.
3. Insert the current logger in series with the supply input.
4. Configure the logger to capture both average consumption and short current peaks. A sampling interval of 100 ms or faster is preferred where practical.
5. Power on the complete node.
6. Allow the node to initialise and join the LoRaWAN network.
7. Start continuous logging.
8. Operate the node normally, including sensor acquisition, sleep periods, aggregation, and LoRaWAN transmission.
9. Continue logging for 24 hours without interrupting normal operation.
10. Export the recorded current-versus-time data.
11. Calculate the time-weighted average current.
12. Identify peak current during LoRa transmission.
13. Compare measured consumption against the initial power budget.

Average current:

\[
I_{\text{avg}}=
\frac{1}{T}\int_0^T I(t)\,dt
\]

For discrete logger samples:

\[
I_{\text{avg}}=
\frac{\sum I_k\Delta t_k}{\sum\Delta t_k}
\]

**Pass criteria:**

- A continuous 24-hour current measurement is completed.
- Active, sleep, and transmission current levels are identifiable.
- Average current consumption is quantified.
- No supply instability or unexpected resets occur.

The estimated target of less than 0.45 mA is used as a design benchmark, not as a substitute for measured results.

**Important:** The measured current must be reported at the 3.6 V bench-supply input. The measurement must include the boost converter and all circuitry powered by that input.

### TEST-08: Field Deployment Test

**Related requirements:** INT-01 to INT-06, COM-01 to COM-06.

**Objective:** Demonstrate that the complete network operates under real outdoor conditions.

**Procedure:**

1. Install the three sensor nodes at selected outdoor locations.
2. Install and activate the LoRaWAN gateway.
3. Verify the operation of each node before deployment.
4. Start continuous 10-minute measurement and transmission cycles.
5. Monitor gateway packet reception.
6. Record packet reception statistics for each node.
7. Collect wind-speed, direction, and temperature data.
8. Compare trends between the three nodes.
9. Identify missing packets, sensor anomalies, and unexpected interruptions.
10. Compare temperature trends with an independent local reference if available.
11. Document environmental conditions and node installation positions.

**Minimum observation period:** At least 3 hours and 20 minutes, corresponding to 20 scheduled transmission opportunities per node. Longer observation is preferred.

**Pass criteria:**

- All three nodes operate outdoors.
- At least 95% packet success rate is achieved over the observation period.
- Measurements are correctly associated with their respective nodes.
- Data is received at approximately 10-minute intervals.
- Measurement trends are physically plausible and can be compared across nodes.

The field test demonstrates short-term functional feasibility. It does not establish long-term weather resistance or measurement stability.

---

## 5. Final Verification Report

The final report must contain:

- Completed test procedures.
- Measured values and reference values.
- Pass/fail status for each requirement.
- Wind-speed calibration curve.
- Wind-direction calibration curve.
- Temperature comparison.
- Bearing starting-torque results.
- 24-hour current measurement.
- LoRaWAN packet success statistics.
- Outdoor field-test observations.
- List of requirements not verified and reasons.

No requirement may be marked as passed solely on the basis of a calculation or simulation when physical verification is required.
