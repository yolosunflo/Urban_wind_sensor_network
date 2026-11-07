#pragma once

namespace uwsn {

// Abstract temperature sensor: the rest of the firmware does not care whether it
// is analog (TMP36, NTC) or digital (DS18B20, SHT31). Swap the implementation
// once the real reference is chosen.
class ITemperatureSensor {
 public:
  virtual ~ITemperatureSensor() = default;
  virtual bool begin() = 0;
  virtual bool read(float& tempC) = 0;   // false = sensor fault / disconnected
};

// Basic linear analog sensor: T = (V - V0) / slope  (defaults in config.h).
class AnalogTemperatureSensor : public ITemperatureSensor {
 public:
  explicit AnalogTemperatureSensor(int pin);
  bool begin() override;
  bool read(float& tempC) override;
 private:
  int pin_;
};

// TODO if we choose a digital sensor (e.g. DS18B20 over 1-Wire, SHT31 over I2C):
// class DigitalTemperatureSensor : public ITemperatureSensor { ... };

}  // namespace uwsn
