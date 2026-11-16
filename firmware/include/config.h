#pragma once
#include <stdint.h>

// ---- Anemometer selection ----
// We only use our own anemometer (ANEMO_PULSE). The analog driver is kept for reference.
#define ANEMO_ANALOG       1      // two analog voltage outputs (speed + vane)
#define ANEMO_PULSE        2      // our own: reed switch + AS5600
#define ANEMOMETER_TYPE    ANEMO_PULSE

// ---- Hardware: Seeed LoRa-E5 mini (STM32WLE5JC) ----
// Do NOT use PA4, PA5 (RF switch), PB0 (radio TCXO), PB13 (BOOT button), PA13/PA14 (SWD).
#define PIN_I2C_SDA        PA15   // I2C2, shared by the AS5600 and the TMP102
#define PIN_I2C_SCL        PB15
#define PIN_REED           PB4    // reed switch to GND, internal pull-up (any free pin with interrupt)
#define PIN_ANEMO_POWER    -1     // AS5600 on the 3V3 rail, not power-gated
#define PIN_BATTERY_ADC    PB3    // ADC input: battery + -> R1 -> PB3 -> R2 -> GND

// Analog anemometer only (not wired on our board, kept for reference)
#define PIN_SPEED_ADC      -1
#define PIN_DIR_ADC        -1
#define PIN_SENSOR_POWER   -1

#define ADC_BITS           12
#define ADC_VREF           3.3f   // volts (3V3 rail of the board)
#define BATTERY_DIVIDER    2.0f   // (R1 + R2) / R2, e.g. two 1 MOhm resistors
#define BATTERY_ADC_AVG    8      // ADC readings averaged per battery measurement

// ---- Sampling / aggregation (only these four numbers are typed by hand) ----
#define SAMPLE_PERIOD_MS   1000   // internal sampling at 1 Hz
#define WINDOW_S           600    // one uplink per window (MUST match window_s in server/uwsn/config.py)
#define BURST_S            300    // how long we sample inside a window (<= WINDOW_S, saves battery)
#define SENSOR_WARMUP_MS   2000   // analog anemometer warm-up after power-on

// Derived values: use these, never retype the numbers
#define WINDOW_MS          (WINDOW_S * 1000UL)
#define BURST_MS           (BURST_S * 1000UL)
#define SAMPLES_PER_BURST  (BURST_MS / SAMPLE_PERIOD_MS)
static_assert(BURST_S <= WINDOW_S, "the sampling burst must fit inside the window");
static_assert(BURST_MS % SAMPLE_PERIOD_MS == 0, "BURST_S must be a whole number of sample periods");
static_assert(SAMPLES_PER_BURST <= 65535, "sample counters are uint16");

// ---- Quality thresholds of one window ----
#define MIN_SAMPLE_RATIO   0.8f   // fewer good samples than this share of SAMPLES_PER_BURST -> Q_FEW_SAMPLES
#define SENSOR_FAULT_RATIO 0.5f   // more failed reads than this share -> Q_SENSOR_FAULT (wind unusable)

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

// ---- Uplink payload scaling (fixed-point, see docs/payload_format.md) ----
#define PAYLOAD_VERSION    1
#define UPLINK_PORT        1
#define SPEED_LSB_MS       0.01f   // uint16 -> 0 .. 655.35 m/s
#define DIR_LSB_DEG        0.1f    // uint16 -> 0 .. 359.9 deg
#define STD_LSB_MS         0.05f   // uint8  -> 0 .. 12.75 m/s
#define TEMP_LSB_C         0.01f   // int16  -> -327.68 .. 327.67 C
#define BATTERY_OFFSET_V   2.0f
#define BATTERY_LSB_V      0.01f   // uint8  -> 2.00 .. 4.55 V

// ---- Downlink: calibration commands (see docs/payload_format.md) ----
#define DOWNLINK_PORT        2
#define DOWNLINK_MAX_SIZE    64     // bigger than any command we accept
#define CMD_SET_CALIB        0x01   // 9 bytes: cmd, gain, speed offset, dir offset, temp offset
#define CMD_RESET_CALIB      0x02   // 1 byte: back to the defaults
#define DOWNLINK_CALIB_SIZE  9
#define CALIB_GAIN_LSB       0.0001f  // uint16 -> 0 .. 6.5535 m/s per Hz
#define CALIB_OFFSET_LSB_MS  0.001f   // int16  -> +-32.767 m/s
#define CALIB_DIR_LSB_DEG    0.1f     // int16  -> +-3276.7 deg (server sends -180..180)
#define CALIB_TEMP_LSB_C     0.01f    // int16  -> +-327.67 C
#define CALIB_EEPROM_ADDR    0        // where the calibration is stored in the emulated EEPROM

// ---- Temperature sensor (SparkFun SEN-13314 = TI TMP102, I2C) ----
#define TEMP_I2C_ADDR         0x48    // ADD0 on GND (0x49 = VCC, 0x4A = SDA, 0x4B = SCL)
#define TEMP_CONVERSION_MS    35      // one-shot conversion time (datasheet max)
#define TEMP_SAMPLE_EVERY_N   10      // read temperature every N wind samples (it changes slowly)
#define TEMP_MIN_C           -20.0f   // plausible range (outside = sensor fault)
#define TEMP_MAX_C            60.0f

// ---- Stuck-sensor detection (TBD: tune with field data) ----
#define STUCK_MIN_SPEED_MS   1.0f   // above this speed the vane always moves a little
#define STUCK_DIR_TOL_DEG    1.0f   // smaller change = vane did not move
#define STUCK_VANE_N         120    // windy samples in a row with a frozen vane -> vane stuck
#define STUCK_CUPS_MOVES     60     // vane moved this often in a window with 0 m/s the whole time -> cups/reed stuck
