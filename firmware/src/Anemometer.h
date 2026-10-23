#pragma once
#include "types.h"

namespace uwsn {

// Abstract sensor: lets us swap the analog model for pulse or RS485/ultrasonic
// without touching the rest of the firmware.
class IAnemometer {
 public:
  virtual ~IAnemometer() = default;
  virtual bool begin() = 0;
  virtual bool read(RawSample& out) = 0;   // false = sensor fault
  virtual void powerOn() = 0;
  virtual void powerOff() = 0;
};

// Analog output (voltage proportional to speed, potentiometer vane).
class AnalogAnemometer : public IAnemometer {
 public:
  AnalogAnemometer(int speedPin, int dirPin, int powerPin);
  bool begin() override;
  bool read(RawSample& out) override;
  void powerOn() override;
  void powerOff() override;
 private:
  int speedPin_, dirPin_, powerPin_;
};

// TODO if the chosen model outputs pulses (reed switch): PulseAnemometer
// counting interrupts over a gate time, speed = f(pulse frequency).

}  // namespace uwsn
