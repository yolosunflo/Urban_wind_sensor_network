#include "Calibration.h"
#include "config.h"

namespace uwsn {

bool Calibration::load() { /* TODO */ return true; }
bool Calibration::save() const { /* TODO */ return true; }

WindSample Calibration::apply(const RawSample& r) const {
  const float full = (1 << ADC_BITS) - 1;
  const float vSpeed = r.speedAdc * ADC_VREF / full;
  const float vDir   = r.dirAdc   * ADC_VREF / full;

  WindSample s;
  s.speed_ms = (vSpeed - params_.speedOffsetV) * params_.speedGain;
  if (s.speed_ms < 0) s.speed_ms = 0;
  // Potentiometer vane: 0..Vref maps to 0..360 deg (TODO: check real sensor)
  float dir = vDir / ADC_VREF * 360.0f + params_.dirOffsetDeg;
  while (dir >= 360.0f) dir -= 360.0f;
  while (dir < 0.0f)    dir += 360.0f;
  s.dir_deg = dir;
  s.tMs = r.tMs;
  return s;
}

bool Calibration::isDue(uint32_t nowUnix) const {
  if (params_.calibratedAt == 0) return true;
  return (nowUnix - params_.calibratedAt) > params_.validForDays * 86400UL;
}

}  // namespace uwsn
