#pragma once
#include <stdint.h>

namespace uwsn {

// Bit flags describing the quality of one aggregate window.
enum QualityFlag : uint8_t {
  Q_OK               = 0,
  Q_OUT_OF_RANGE     = 1 << 0,
  Q_STUCK            = 1 << 1,
  Q_SPIKE            = 1 << 2,
  Q_LOW_BATTERY      = 1 << 3,
  Q_CALIBRATION_DUE  = 1 << 4,
  Q_SENSOR_FAULT     = 1 << 5,
  Q_FEW_SAMPLES      = 1 << 6,
};

// Raw ADC counts, straight from the anemometer (no physics yet).
struct RawSample {
  uint16_t speedAdc;
  uint16_t dirAdc;
  uint32_t tMs;
};

// Physical values after calibration (float is fine inside the MCU).
struct WindSample {
  float    speed_ms;
  float    dir_deg;      // 0..360, direction wind comes FROM
  uint32_t tMs;
};

// Result of one aggregation window (still float).
struct WindAggregate {
  float    meanSpeed_ms;
  float    gust_ms;
  float    meanDir_deg;
  float    stdSpeed_ms;
  uint16_t nSamples;
  uint8_t  flags;        // QualityFlag bitmask
};

// What goes over the air: fixed-point integers only.
struct UplinkFrame {
  uint8_t  version;
  uint16_t seq;
  uint16_t meanSpeed;    // x 0.01 m/s
  uint16_t gust;         // x 0.01 m/s
  uint16_t meanDir;      // x 0.1 deg
  uint8_t  stdSpeed;     // x 0.05 m/s
  int16_t  temp;         // x 0.01 C (INT16_MIN = not available)
  uint8_t  battery;      // 2.00 V + 0.01 V * value
  uint8_t  flags;
};

constexpr uint8_t UPLINK_SIZE = 14;

}  // namespace uwsn
