#pragma once
#include <stdint.h>

// ---- Hardware (TODO: adapt to the chosen board) ----
#define PIN_SPEED_ADC      34     // anemometer speed channel (analog)
#define PIN_DIR_ADC        35     // wind vane channel (analog)
#define PIN_SENSOR_POWER   25     // MOSFET to power-gate the sensor
#define PIN_BATTERY_ADC    32     // battery voltage divider

#define ADC_BITS           12
#define ADC_VREF           3.3f   // volts
#define BATTERY_DIVIDER    2.0f

// ---- Sampling / aggregation ----
#define SAMPLE_PERIOD_MS   1000   // internal sampling at 1 Hz
#define WINDOW_S           600    // one uplink per 10 minutes
#define BURST_S            600    // how long we actually sample inside a window
                                  // (< WINDOW_S to save battery, see docs)
#define SENSOR_WARMUP_MS   2000

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
