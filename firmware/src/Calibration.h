#pragma once
#include "types.h"

namespace uwsn {

// Per-node calibration, stored in non-volatile memory and updatable by downlink.
struct CalibrationParams {
  float    speedOffsetV  = 0.0f;   // voltage at 0 m/s
  float    speedGain     = 1.0f;   // m/s per volt (from datasheet / wind tunnel)
  float    dirOffsetDeg  = 0.0f;   // mounting orientation correction
  uint32_t calibratedAt  = 0;      // unix time of last calibration
  uint32_t validForDays  = 180;    // after this, Q_CALIBRATION_DUE
};

class Calibration {
 public:
  bool load();                          // TODO: read from NVS / EEPROM
  bool save() const;                    // TODO
  void set(const CalibrationParams& p) { params_ = p; }
  const CalibrationParams& params() const { return params_; }

  WindSample apply(const RawSample& raw) const;   // ADC counts -> m/s, deg
  bool isDue(uint32_t nowUnix) const;

 private:
  CalibrationParams params_;
};

}  // namespace uwsn
