#pragma once
#include <stdint.h>

// ---- Anemometer selection ----
#define ANEMO_ANALOG       1      // two analog voltage outputs (speed + vane)
#define ANEMO_PULSE        2      // our own: reed switch + AS5600
#define ANEMOMETER_TYPE    ANEMO_PULSE

// ---- Hardware (TODO: adapt to the chosen board) ----
#define PIN_SPEED_ADC      34     // analog anemometer: speed channel
#define PIN_DIR_ADC        35     // analog anemometer: wind vane channel
#define PIN_SENSOR_POWER   25     // analog anemometer: MOSFET to power-gate the sensor
#define PIN_BATTERY_ADC    32     // battery voltage divider

#define PIN_REED           26     // our anemometer: reed switch GPIO (other side on GND)
#define PIN_ANEMO_POWER    -1     // our anemometer: AS5600 power pin, -1 = always on (3V3 rail)

#define ADC_BITS           12
#define ADC_VREF           3.3f   // volts
#define BATTERY_DIVIDER    2.0f

// ---- Sampling / aggregation ----
#define SAMPLE_PERIOD_MS   1000   // internal sampling at 1 Hz
#define WINDOW_S           300    // one uplink per 5 minutes
#define BURST_S            600    // how long we actually sample inside a window (< WINDOW_S to save battery)
#define SENSOR_WARMUP_MS   2000   // analog anemometer warm-up after power-on

// ---- Analog anemometer ----
#define ANEMO_ADC_AVG          8   // ADC readings averaged per sample
#define ANEMO_ADC_RAIL_MARGIN  20  // counts below full scale considered "stuck at rail" (fault)

// ---- Our anemometer (reed switch + AS5600) ----
#define REED_DEBOUNCE_US   2000   // ignore edges closer than this (contact bounce); caps at 500 Hz
#define AS5600_I2C_ADDR    0x36   // fixed I2C address of the AS5600
#define AS5600_STARTUP_MS  10     // power-up time before the first I2C read

// ---- Plausibility limits (on-node sanity check) ----
#define SPEED_MAX_MS       60.0f
#define LOW_BATTERY_V      3.3f

// ---- Payload scaling (fixed-point, see docs/payload_format.md) ----
#define PAYLOAD_VERSION    1
#define SPEED_LSB_MS       0.01f   // uint16 -> 0 .. 655.35 m/s
#define DIR_LSB_DEG        0.1f    // uint16 -> 0 .. 359.9 deg
#define STD_LSB_MS         0.05f   // uint8  -> 0 .. 12.75 m/s
#define TEMP_LSB_C         0.01f   // int16  -> -327.68 .. 327.67 C
#define BATTERY_OFFSET_V   2.0f
#define BATTERY_LSB_V      0.01f   // uint8  -> 2.00 .. 4.55 V

// ---- Temperature sensor (SparkFun SEN-13314 = TI TMP102, I2C) ----
#define TEMP_I2C_ADDR         0x48    // ADD0 on GND (0x49 = VCC, 0x4A = SDA, 0x4B = SCL)
#define TEMP_CONVERSION_MS    35      // one-shot conversion time (datasheet max)
#define TEMP_SAMPLE_EVERY_N   10      // read temperature every N wind samples (it changes slowly)
#define TEMP_MIN_C           -20.0f   // plausible range (outside = sensor fault)
#define TEMP_MAX_C            60.0f