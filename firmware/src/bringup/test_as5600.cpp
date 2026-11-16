// Test 4: AS5600 magnetic angle sensor (wind vane).
// Prints 5 times per second: magnet status, magnet strength (AGC) and the angle.
// Check: "magnet OK" all the time, AGC roughly in the middle, and the angle goes smoothly
// from 0 to 360 deg when you turn the vane one full turn, without jumps.
#include "bringup.h"

// AS5600 registers (datasheet)
constexpr uint8_t REG_STATUS = 0x0B, REG_RAW_ANGLE = 0x0C, REG_AGC = 0x1A;
constexpr uint8_t ST_MH = 1 << 3, ST_ML = 1 << 4, ST_MD = 1 << 5;

static bool readRegs(uint8_t reg, uint8_t* buf, uint8_t n) {
  Wire.beginTransmission(AS5600_I2C_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)AS5600_I2C_ADDR, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

void setup() {
  bringupBegin("AS5600 angle sensor (vane)");
  i2cBegin();
  Wire.beginTransmission(AS5600_I2C_ADDR);
  const bool ok = (Wire.endTransmission() == 0);
  printResult(ok, F("AS5600 answers at 0x36"));
  if (!ok) LOG.println(F("-> run test_i2c first"));
  LOG.println(F("\nAGC = how hard the chip amplifies the magnet field: near 0 = magnet too close,"));
  LOG.println(F("near 255 (128 in 3.3 V mode) = too far. Aim for the middle.\n"));
}

void loop() {
  uint8_t status, agc, a[2];
  if (!readRegs(REG_STATUS, &status, 1) || !readRegs(REG_AGC, &agc, 1) || !readRegs(REG_RAW_ANGLE, a, 2)) {
    LOG.println(F("I2C error: AS5600 not answering"));
    delay(1000);
    return;
  }
  const uint16_t raw = ((a[0] & 0x0F) << 8) | a[1];
  LOG.print(status & ST_MD ? F("magnet OK      ") : F("NO MAGNET      "));
  if (status & ST_MH) LOG.print(F("(too strong/close) "));
  if (status & ST_ML) LOG.print(F("(too weak/far)     "));
  LOG.print(F("AGC "));
  LOG.print(agc);
  LOG.print(F("   raw "));
  LOG.print(raw);
  LOG.print(F("   angle "));
  LOG.print(raw * 360.0f / 4096.0f, 1);
  LOG.println(F(" deg"));
  delay(200);
}
