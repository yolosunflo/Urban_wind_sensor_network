# DOCUMENT 3 — POWER BUDGET AND DUTY CYCLE ANALYSIS

**Project:** Urban Wind Sensor Network  
**Version:** 1.0 — Preliminary Estimation  
**Purpose:** Establish an initial power-consumption estimate to guide future battery selection.

## 1. Scope and Assumptions

The prototype will be powered by an external bench power supply rather than a battery.

A nominal 3.6 V DC input rail is assumed for preliminary calculations. The TPS61023 boost converter provides a 5 V rail where required.

The Wio-E5 Mini operates from an appropriate regulated logic supply. The 3.6 V input **must not be connected directly to a 3.3 V-only supply pin.**

The following assumptions are used:

| Parameter | Assumption |
|---|---|
| Bench supply voltage | 3.6 V |
| Measurement interval | 10 minutes |
| Analysis duration | 30 minutes |
| Number of measurement cycles | 3 |
| MCU active current | 8 mA |
| MCU sleep current | 15 µA |
| LoRa transmission current | 45 mA |
| LoRa transmission duration | 1.2 seconds per cycle |
| LoRa reception current | 12 mA |
| Reception duration | 2 seconds per cycle |
| Magnetic sensor | Passive reed switch or low-power Hall sensor |
| Hall sensor current assumption | 10 µA average |
| SHT41 active current assumption | 0.3 mA |
| SHT41 measurement duration | 1 second per cycle |
| Boost converter quiescent current | 20 µA |
| Boost converter efficiency | 85% (assumption for switched 5 V load) |

These values are preliminary engineering assumptions, not measured component specifications. Actual values depend on the selected operating mode, radio configuration, board implementation, and firmware.

## 2. Duty Cycle

Each 10-minute cycle is divided into:

1. Sensor acquisition and processing.
2. LoRaWAN transmission.
3. LoRaWAN reception window.
4. Low-power sleep.

The assumed timing is:

| Operating State | Duration per 10-minute cycle |
|---|---:|
| MCU active processing | 2 seconds |
| LoRa transmission | 1.2 seconds |
| LoRa reception | 2 seconds |
| Remaining sleep time | 594.8 seconds |

The SHT41 is activated during the acquisition period.

Wind-speed pulse detection is assumed to operate with negligible additional average consumption using a passive reed switch.

## 3. Estimated Average Current Over 30 Minutes

The following calculations use equivalent current referred to the 3.6 V bench-supply input.

| Component / Operating State | Current | Duration over 30 min | Average Input Current |
|---|---:|---:|---:|
| Wio-E5 active processing | 8 mA | 6 s | 0.0267 mA |
| Wio-E5 sleep | 0.015 mA | 1,784.4 s | 0.0149 mA |
| LoRa TX | 45 mA | 3.6 s | 0.0900 mA |
| LoRa RX | 12 mA | 6 s | 0.0400 mA |
| Magnetic sensor | 0.010 mA | 1,800 s | 0.0100 mA |
| SHT41 | 0.3 mA | 3 s | 0.0005 mA |
| TPS61023 quiescent current | 0.020 mA | 1,800 s | 0.0200 mA |
| Switched 5 V load | 5 mA at 5 V | 3 s | 0.0136 mA |
| **Total estimated average** | | | **0.2157 mA** |

The sleep duration excludes active processing, transmission, and reception:

\[
t_{\text{sleep}}=1800-6-3.6-6
\]

\[
t_{\text{sleep}}=1784.4\text{ s}
\]

For the switched 5 V load, the equivalent current at the 3.6 V input is estimated as:

\[
I_{\text{input}}=
\frac{V_{\text{out}}I_{\text{out}}}
{V_{\text{in}}\eta}
\]

\[
I_{\text{input}}=
\frac{5\times0.005}
{3.6\times0.85}
=8.17\text{ mA}
\]

This load is only active for three seconds over the 30-minute period.

### 3.1 Average Current Calculation

For each operating state:

\[
I_{\text{avg},i}=
I_i\frac{t_i}{T}
\]

The total average current is:

\[
I_{\text{avg}}=
\sum_i I_{\text{avg},i}
\]

Therefore:

\[
I_{\text{avg}}\approx0.216\text{ mA}
\]

### 3.2 Design Margin

A 25% engineering margin is applied to account for uncertainties in component consumption, radio behaviour, and implementation.

\[
I_{\text{design}}=
0.216\times1.25
\]

\[
\boxed{I_{\text{design}}\approx0.270\text{ mA}}
\]

<badge color="success">Below preliminary target</badge>

The preliminary target is:

\[
\boxed{I_{\text{avg}}<0.45\text{ mA}}
\]

The estimated consumption, including the design margin, remains below this target.

## 4. Interpretation and Limitations

The estimated average current is intended to establish a preliminary design direction, not to demonstrate actual battery autonomy.

Important considerations:

- LoRa transmission current depends on transmit power, spreading factor, and radio configuration.
- The Wio-E5 Mini development board may consume more current than the bare radio module because of additional board circuitry.
- A passive reed switch has negligible static current, whereas a Hall sensor introduces a continuous or periodic current depending on its implementation.
- The TPS61023 quiescent current must be confirmed for the selected operating conditions.
- The 5 V load is an illustrative switched load, not a confirmed final hardware consumption.
- The estimate assumes that the MCU, radio, and converter current values can be represented at the stated reference supply. Actual rail conversions, regulator losses, and simultaneous loads must be accounted for in the final measured circuit.
- Gateway consumption is excluded because this document concerns individual sensor nodes.

The estimate must be updated when the final electrical schematic and component configuration are available.

## 5. Power Measurement and Validation

The estimated current will be validated through the 24-hour Power Measurement Test defined in the Verification and Test Plan.

The measurement will use:

- A 3.6 V bench power supply.
- A current logger connected in series with the supply.
- The fully assembled sensor node.
- Normal sensor acquisition and LoRaWAN transmission cycles.

The measured average current will be compared against:

| Parameter | Target |
|---|---:|
| Preliminary estimated average | 0.216 mA |
| Estimated average with 25% margin | 0.270 mA |
| Maximum design target | 0.450 mA |

**Important:** The actual measured current, rather than the estimated value, will be used for subsequent battery sizing.

## 6. Future Battery Selection

Battery selection is deferred until the power measurement test has been completed.

The following parameters will be required:

- Measured average current.
- Peak current during LoRa transmission.
- Required operating voltage.
- Battery discharge characteristics.
- Converter efficiency.
- Available battery capacity.
- Expected operating temperature range.

Battery autonomy will subsequently be estimated using:

\[
t_{\text{autonomy}}=
\frac{C_{\text{usable}}}{I_{\text{avg}}}
\]

where capacity is expressed in mAh and average current in mA.

No battery lifetime claim is made at the PoC stage.
