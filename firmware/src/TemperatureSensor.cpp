#include "TemperatureSensor.h"
#include "config.h"
#include <Arduino.h>

namespace uwsn {

// TMP102 registers (datasheet of the SEN-13314 chip), fixed by the chip so not in config.h
constexpr uint8_t REG_TEMP   = 0x00;
constexpr uint8_t REG_CONFIG = 0x01;

// Configuration register, first byte: bit 7 = OS (one-shot), bit 0 = SD (shutdown)
constexpr uint8_t CFG_SD = 0x01;
constexpr uint8_t CFG_OS = 0x80;
// Second byte: default value (4 Hz rate, normal 12-bit mode, not extended)
constexpr uint8_t CFG_LSB = 0xA0;

TemperatureSensor::TemperatureSensor(TwoWire& wire) : wire_(wire) {}

bool TemperatureSensor::begin() {
  wire_.begin();
  return writeConfig(CFG_SD, CFG_LSB);   // also checks the sensor answers
}

bool TemperatureSensor::read(float& tempC) {
  // Start one conversion (the sensor goes back to shutdown by itself afterwards)
  if (!writeConfig(CFG_OS | CFG_SD, CFG_LSB)) return false;
  delay(TEMP_CONVERSION_MS);

  uint8_t b[2];
  if (!readRegs(REG_TEMP, b, 2)) return false;

  // 12-bit signed value stored in the top 12 bits of the 16 (bottom 4 bits are 0),
  // so the 16-bit signed number / 256 gives degrees directly (1 step = 1/16 = 0.0625 C)
  const int16_t raw = (int16_t)((b[0] << 8) | b[1]);
  tempC = raw / 256.0f;

  // Outside the plausible range = faulty sensor or corrupted reading
  return tempC > TEMP_MIN_C && tempC < TEMP_MAX_C;
}

bool TemperatureSensor::writeConfig(uint8_t msb, uint8_t lsb) {
  wire_.beginTransmission(TEMP_I2C_ADDR);
  wire_.write(REG_CONFIG);
  wire_.write(msb);
  wire_.write(lsb);
  return wire_.endTransmission() == 0;
}

bool TemperatureSensor::readRegs(uint8_t reg, uint8_t* buf, uint8_t n) {
  wire_.beginTransmission(TEMP_I2C_ADDR);
  wire_.write(reg);
  if (wire_.endTransmission(false) != 0) return false;   // repeated start, keep the bus
  if (wire_.requestFrom((uint8_t)TEMP_I2C_ADDR, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = wire_.read();
  return true;
}

}  // namespace uwsn