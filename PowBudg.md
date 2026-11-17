# DOCUMENT 3 — POWER BUDGET AND DUTY CYCLE ANALYSIS

**Project:** Urban Wind Sensor Network  
**Version:** 1.1 — Preliminary Estimation (aligned with firmware timing)  
**Purpose:** Establish an initial power-consumption estimate to guide future battery selection.

## 1. Scope and Assumptions

The prototype is powered by an external 3.6 V bench supply instead of a battery. A TPS61023 boost converter generates 5 V for the LoRa-E5 mini, whose onboard regulator provides the 3V3 rail used by the sensors.

All currents are expressed **as seen at the 3.6 V input**, in line with how TEST-07 measures them.

Timing comes from `firmware/include/config.h` (see Requirements §1.2). Every window is identical, so one 10-minute window is analysed.

| Parameter | Assumption | Source |
|---|---|---|
| Window | 600 s | `WINDOW_S` |
| Sampling burst | 300 s at 1 Hz (300 samples) | `BURST_S`, `SAMPLE_PERIOD_MS` |
| MCU processing | 2 s per window at 8 mA | assumption |
| LoRa transmission | 1.2 s per window at 45 mA | assumption |
| LoRa reception | 2 s per window at 12 mA (calibration downlink arrives here, no extra wake-up) | assumption |
| MCU sleep current | 15 µA | assumption |
| MCU duty during burst (sleeps between samples, confirmed) | 5 % of each second at 8 mA | assumption for the awake fraction, to measure |
| AS5600 supply current | 6.5 mA typical while powered | datasheet value, **to verify** |
| AS5600 on-time if power-gated | 15 ms per sample (10 ms start-up `AS5600_STARTUP_MS` + read) | assumption |
| TMP102 | about 1 µA shutdown, 35 ms one-shot every 10th sample: about 0.001 mA average | datasheet order of magnitude |
| Reed switch | internal pull-up about 80 µA while the contact is closed, closed about 12 % of the time: 0.010 mA | assumption |
| Battery divider | 2 × 1 MΩ across 3.6 V: 0.0018 mA | `BATTERY_DIVIDER` |
| TPS61023 quiescent current | 20 µA | assumption |

These values are preliminary engineering assumptions, not measured component specifications.

The 5 V switched load and MOSFET of v1.0 are removed: the firmware has no switched load (`PIN_SENSOR_POWER = -1`). The Hall sensor alternative is dropped: the node uses a reed switch.

## 2. Duty Cycle

| Operating state | Duration per 600 s window |
|---|---:|
| Sampling burst (1 Hz) | 300 s |
| MCU processing | 2 s |
| LoRa transmission | 1.2 s |
| LoRa reception | 2 s |
| Deep sleep | 294.8 s |

The MCU sleeps between samples. The AS5600 is the dominant unknown: `PIN_ANEMO_POWER = -1` means it is currently **always powered on the 3V3 rail**, not gated. Two scenarios bracket the result:

- **A, as configured today:** AS5600 always on.
- **B:** AS5600 power-gated and only on during each sample (requires a power pin, ICD-07).

## 3. Estimated Average Current

| Component / state | A (mA) | B (mA) |
|---|---:|---:|
| MCU during burst (300 s) | 0.2000 | 0.2000 |
| MCU sleep (remaining time) | 0.0145 | 0.0145 |
| MCU processing (2 s) | 0.0267 | 0.0267 |
| LoRa TX (1.2 s) | 0.0900 | 0.0900 |
| LoRa RX (2 s) | 0.0400 | 0.0400 |
| AS5600 | 6.5000 | 0.0488 |
| TMP102 | 0.0010 | 0.0010 |
| Reed switch pull-up | 0.0100 | 0.0100 |
| Battery divider | 0.0018 | 0.0018 |
| TPS61023 quiescent | 0.0200 | 0.0200 |
| **Total average** | **6.90** | **0.453** |
| **With 25 % margin** | **8.6** | **0.566** |

Average current of each state:

$$
I_{\text{avg},i}=I_i\frac{t_i}{T},\qquad I_{\text{avg}}=\sum_i I_{\text{avg},i},\qquad T=600\ \text{s}
$$

Examples: LoRa TX gives $45 \times 1.2/600 = 0.090$ mA. The AS5600 in B gives $6.5 \times 0.015 \times 300/600 = 0.049$ mA. The MCU gives $8 \times 0.05 \times 300/600 = 0.200$ mA.

The 25 % margin covers uncertainty in component consumption, radio behaviour and implementation.

## 4. Result against the target

The preliminary target is $I_{\text{avg}} < 0.45$ mA.

| Scenario | Average | With margin | Target met? |
|---|---:|---:|---|
| A | 6.90 mA | 8.6 mA | No |
| B | 0.453 mA | 0.566 mA | Borderline without margin, no with margin |

**The v1.0 estimate (0.216 mA) was obtained with a 2 s active period and without the AS5600.** With the real timing (5-minute burst) and the AS5600 included, the target is not met by the current configuration.

Main levers, in order of impact:

1. **AS5600 power** (6.5 mA typical): power-gate it (needs a GPIO or a switch) or use its low-power mode if the reading rate allows.
2. **MCU awake time per sample** (5 % assumed): shorten I²C reads and processing.
3. **Burst length (`BURST_S`):** burst-related terms scale with it; this trades sampling statistics for power.
4. **Reed pull-up:** if the rotor stops with the magnet on the switch, the pull-up draws about 80 µA continuously, which alone is a large part of the budget.

## 5. Interpretation and Limitations

- The conclusions depend on the MCU awake fraction and on the AS5600 current; both must be confirmed (datasheet, TEST-07).
- LoRa transmission current depends on transmit power, spreading factor and radio configuration.
- The LoRa-E5 mini board may consume more than the bare module because of additional board circuitry.
- Currents are referred to the 3.6 V input without detailed conversion losses. If the board derives 3V3 from the 5 V rail with a linear regulator, input-side currents are about 1.6 times higher ($5/(3.6\times0.85)$ at 85 % boost efficiency).
- The TPS61023 quiescent current and its efficiency at light load must be confirmed.
- Gateway consumption is excluded.

## 6. Power Measurement and Validation

The estimate will be validated by the 24-hour Power Measurement Test (TEST-07 in the Verification and Test Plan), with:

- A 3.6 V bench power supply.
- A current logger in series with the supply (sampling 100 ms or faster).
- The fully assembled node running the **final timing (600 s window, 300 s burst)**, not the 60 s / 30 s debug values.

Targets for comparison:

| Parameter | Value |
|---|---:|
| Estimate B (gated AS5600) | 0.453 mA |
| Estimate A (AS5600 always on) | 6.90 mA |
| Maximum design target | 0.450 mA |

The measured current, not the estimate, will be used for battery sizing.

## 7. Future Battery Selection

Battery selection is deferred until TEST-07 is completed. Required inputs: measured average current, peak current during LoRa transmission, operating voltage, discharge characteristics, converter efficiency, available capacity, operating temperature range.

$$
t_{\text{autonomy}}=\frac{C_{\text{usable}}}{I_{\text{avg}}}
$$

with capacity in mAh and current in mA. No battery lifetime claim is made at the PoC stage.
