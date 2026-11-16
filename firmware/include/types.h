#pragma once
#include <stdint.h>

namespace uwsn {

// Bit flags describing the quality of one aggregate window.
enum QualityFlag : uint8_t {
  Q_OK               = 0,
  Q_OUT_OF_RANGE     = 1 << 0,
  Q_STUCK            = 1 << 1,
  Q_SPIKE            = 1 << 2, // not used on the node (the server detects spikes)
  Q_LOW_BATTERY      = 1 << 3,
  Q_CALIBRATION_DUE  = 1 << 4, // not used: the node has no clock, the server decides
  Q_SENSOR_FAULT     = 1 << 5,
  Q_FEW_SAMPLES      = 1 << 6,
  Q_TEMP_FAULT       = 1 << 7,
};

struct RawSample {
  uint16_t speedAdc;   // analog anemometer: ADC count of the speed output
  uint16_t dirAdc;     // analog anemometer: ADC count of the vane output
  uint16_t pulses;     // pulse anemometer: pulses counted since the previous sample
  uint16_t dtMs;       // pulse anemometer: time covered by those pulses
  uint16_t angleRaw;   // AS5600 angle, 0..4095
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
  bool     hasTemp;
  float    meanTemp_c;
  uint16_t nSamples;
  uint8_t  flags;
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
