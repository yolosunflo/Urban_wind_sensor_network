#include "Calibration.h"
#include "config.h"

namespace uwsn {

// Base class

float Calibration::applyTemp(float rawTempC) const {
  return rawTempC + common().tempOffsetC;
}

float Calibration::correctDirection(float rawDeg) const {
  float dir = rawDeg + common().dirOffsetDeg;
  while (dir >= 360.0f) dir -= 360.0f;
  while (dir < 0.0f)    dir += 360.0f;
  return dir;
}


// Analog anemometer

WindSample AnalogCalibration::apply(const RawSample& r) const {
  // ADC counts to volts
  const float full   = (1 << ADC_BITS) - 1;
  const float vSpeed = r.speedAdc * ADC_VREF / full;
  const float vDir   = r.dirAdc   * ADC_VREF / full;

  WindSample s{};
  s.speed_ms = (vSpeed - params_.speedOffsetV) * params_.speedGain;
  if (s.speed_ms < 0) s.speed_ms = 0;         // noise below the offset
  s.dir_deg = correctDirection(vDir / ADC_VREF * 360.0f);
  return s;
}


// Our own anemometer (pulses + AS5600)

WindSample PulseCalibration::apply(const RawSample& r) const {
  WindSample s{};

  // Speed: pulses counted during dtMs -> frequency -> m/s.
  if (r.pulses == 0 || r.dtMs == 0) s.speed_ms = 0.0f;
  else {
    const float freqHz = r.pulses * 1000.0f / r.dtMs;
    s.speed_ms = params_.speedGain * freqHz + params_.speedOffset_ms;
    if (s.speed_ms < 0) s.speed_ms = 0;
  }

  // Direction: AS5600 gives 0..4095 for one full turn.
  s.dir_deg = correctDirection(r.angleRaw * 360.0f / params_.angleCountsPerTurn);
  return s;
}

}  // namespace uwsn