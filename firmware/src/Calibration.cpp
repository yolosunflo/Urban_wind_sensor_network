#include "Calibration.h"
#include "config.h"
#include <EEPROM.h>   // STM32duino: EEPROM emulated in the last flash page

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


// Analog anemometer (kept for reference, not used on our node)

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

namespace {
// What is stored in flash. The magic number tells a saved calibration from blank flash;
// change it whenever PulseCalibParams changes, so an old layout is never read as the new one.
constexpr uint32_t CALIB_MAGIC = 0x55574331;   // "UWC1"
struct StoredCalib {
  uint32_t magic;
  PulseCalibParams params;
};
}  // namespace

bool PulseCalibration::load() {
  StoredCalib s;
  uint8_t* b = reinterpret_cast<uint8_t*>(&s);
  eeprom_buffer_fill();                                   // copy the flash page to RAM once
  for (size_t i = 0; i < sizeof s; i++) b[i] = eeprom_buffered_read_byte(CALIB_EEPROM_ADDR + i);
  if (s.magic != CALIB_MAGIC) return false;               // first boot: keep the defaults
  params_ = s.params;
  return true;
}

void PulseCalibration::save() const {
  const StoredCalib s{CALIB_MAGIC, params_};
  const uint8_t* b = reinterpret_cast<const uint8_t*>(&s);
  eeprom_buffer_fill();
  for (size_t i = 0; i < sizeof s; i++) eeprom_buffered_write_byte(CALIB_EEPROM_ADDR + i, b[i]);
  eeprom_buffer_flush();                                  // one flash page write for the whole struct
}

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
