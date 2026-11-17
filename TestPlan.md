# DOCUMENT 2 — VERIFICATION AND TEST PLAN

**Project:** Urban Wind Sensor Network  
**Version:** 1.1 — Proof of Concept (condensed, linked to `docs/testing.md`)  
**Test configuration:** 2 sensor nodes + 1 LoRaWAN gateway

## 1. Purpose and how this file relates to `docs/testing.md`

This document says **what must be proven** (requirement → test → pass criterion → evidence). `docs/testing.md` says **how to run** the firmware and server tests (commands, wiring, safety rules, gateway setup). Step-by-step firmware procedures are therefore not repeated here.

Each test must produce measurable results and supporting evidence.

| Test | Run with (`docs/testing.md`) | Extra material needed |
|---|---|---|
| TEST-01 | — (mechanical) | torque method, controlled fan, reference anemometer |
| TEST-02 | `test_reed`, `test_bench` (calibration bench) | fan, reference anemometer |
| TEST-03 | `test_as5600`, `test_bench` | marked turntable |
| TEST-04 | `test_i2c`, `test_temperature` | reference thermometer |
| TEST-05 | `pio test -e native`, `python -m pytest`, real firmware | — |
| TEST-06 | `test_radio`, real firmware, gateway setup, `register_sensors.py` | gateway, TTN |
| TEST-07 | real firmware (600 / 300 / 600) | current logger |
| TEST-08 | real firmware | outdoor installation |

Sequence: 01 → 02 → 03/04 → 05 → 07 → 06 → 08 → final review. Use the final timing (`WINDOW_S` 600, `BURST_S` 300) for TEST-07 and TEST-08; the 60 s / 30 s debug values of `testing.md` are for quick tries only.

## 2. Test Equipment

Bench supply (3.6 V), current logger, multimeter, controlled fan, reference anemometer, marked turntable, reference thermometer, LoRaWAN gateway, computer, timestamped logger.

## 3. Tests

### TEST-01: Mechanical starting torque and rotor operation
**Requirements:** MEC-01 to MEC-14, PER-02.  
**Method:** assemble rotor, shaft, bearings and magnet; check alignment; measure bearing starting torque; raise fan airflow gradually while reading a reference anemometer until the rotor starts; at least 5 trials; check pulse detection (`test_reed`).  
**Pass:** starts at 0.3 m/s under the defined conditions; bearing starting torque below calculated aerodynamic torque; no binding or instability; reliable pulse detection.  
**Evidence:** torque measurements, rotor geometry, photographs, starting speeds.

### TEST-02: Wind-speed calibration
**Requirements:** PER-01, PER-02, PER-06, ELE-01 to ELE-05.  
**Method:** fan and reference anemometer side by side; several airflow levels, repeated; log pulse frequency against reference speed (`test_bench` CSV); compute gain and offset on the server (`check_drift()`, `corrected_speed_params()`, `build_downlink()`, `send_downlink()`); repeat with the calibrated node.

$$
|V_{\text{measured}}-V_{\text{reference}}|\leq 0.3+0.03V_{\text{reference}}
$$

(m/s). **Pass:** criterion met over the verified range; rotor detects 0.3 m/s; no significant missed or false pulses (pulse rate stays below the 500 Hz debounce limit at the top speed). Untested ranges must be listed in the final report.

### TEST-03: Wind-direction calibration
**Requirements:** PER-03, PER-04, ELE-06 to ELE-08.  
**Method:** mount the vane on a marked turntable, define 0°, rotate through 360° recording the AS5600 angle (12-bit) at regular steps including around 0°/360° (`test_as5600`); determine the north offset; send it by downlink; repeat at known angles.  
**Pass:** full 0–360° range represented; error ≤ ±10°; correct 0°/360° transition; no discontinuity or ambiguity.

### TEST-04: Temperature calibration
**Requirements:** PER-05, ELE-09.  
**Method:** TMP102 (`test_temperature`) and reference thermometer in the same environment; record simultaneous readings at several temperatures; note the offset; apply it by downlink and re-check.

$$
|T_{\text{measured}}-T_{\text{reference}}|\leq 0.5^\circ C
$$

Valid for the conditions available during the PoC only.

### TEST-05: Data processing and aggregation
**Requirements:** FUN-04 to FUN-06, PER-08, PER-09, PER-10, ELE-14.  
**Method:** unit tests (`pio test -e native`, `python -m pytest`, including `test_end_to_end.py`); then run a real node and compare each record with the raw samples of its 300-sample burst; check circular averaging of direction; check the maximum speed if sent; disconnect a sensor or inject an invalid reading and check the quality flags and server validation.  
**Pass:** one valid record per 10 minutes; aggregates match raw data; node ID from the network and server-assigned timestamp present; invalid readings flagged (few samples, sensor fault, implausible value, stuck vane or cups).

### TEST-06: LoRaWAN communication
**Requirements:** COM-01 to COM-07, FUN-07 to FUN-09.  
**Method:** set up the gateway and register the nodes (see `docs/testing.md`); start all nodes concurrently; compare expected and received uplinks; check decoded payload and node identity; send a calibration downlink, check it is applied after the next uplink and still present after a node reset.

$$
P_{\text{success}}=\frac{N_{\text{received}}}{N_{\text{transmitted}}}\times100
$$

The denominator counts actual transmission attempts, not scheduled ones.  
**Pass:** all nodes communicate; packets decoded and attributed to the right node; at least 95 % of expected packets received; downlink applied and persistent.

### TEST-07: Power measurement (24 h)
**Requirements:** POW-01 to POW-07.  
**Method:** bench supply at 3.6 V (check with multimeter), current logger in series at the supply input (100 ms sampling or faster), complete node with the final timing; join the network, log 24 h without interruption.

$$
I_{\text{avg}}=\frac{\sum I_k\Delta t_k}{\sum\Delta t_k}
$$

Report the time-weighted average, the burst, sleep and transmission levels, and the peak current during TX. The measurement is at the 3.6 V input and includes the boost converter and all circuitry. Compare with the scenarios in PowBudg (scenarios A/B) and state which one the real node matches.  
**Pass:** continuous 24 h measurement; levels identifiable; average quantified; no supply instability or unexpected reset. The 0.45 mA figure is a benchmark, not a pass/fail criterion.

### TEST-08: Field deployment
**Requirements:** INT-01 to INT-06, COM-01 to COM-06.  
**Method:** install two nodes and the gateway outdoors, verify each node first, run continuous 10-minute cycles, record packet statistics per node, compare trends between nodes and with a local temperature reference if available, document positions and conditions.  
**Minimum observation:** 3 h 20 min = 20 scheduled transmissions per node (95 % means at least 19 of 20 received).  
**Pass:** all nodes outdoors; ≥ 95 % packet success; correct node attribution; data at about 10-minute intervals; plausible, comparable trends. The test does not establish long-term weather resistance.

## 4. Final Verification Report

Contents: completed procedures; measured and reference values; pass/fail per requirement; speed and direction calibration curves; temperature comparison; bearing starting torque; 24-hour current measurement against PowBudg; packet success statistics; field observations; list of requirements not verified, with reasons.

No requirement may be marked as passed solely on the basis of a calculation or simulation when physical verification is required.
