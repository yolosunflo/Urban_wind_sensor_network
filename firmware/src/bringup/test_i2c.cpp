// Test 2: I2C bus. Lists every chip answering on SDA PA15 / SCL PB15, every 5 s,
// so you can plug and unplug the sensors and see them appear.
// Expected: 0x36 = AS5600 (vane), 0x48 = TMP102 (temperature, ADD0 on GND).
#include "bringup.h"

static const char* nameOf(uint8_t addr) {
  switch (addr) {
    case AS5600_I2C_ADDR: return "AS5600 angle sensor";
    case 0x48: case 0x49: case 0x4A: case 0x4B:
      return addr == TEMP_I2C_ADDR ? "TMP102 temperature" : "TMP102 at the WRONG address (check ADD0, see config.h)";
    default: return "unknown chip";
  }
}

void setup() {
  bringupBegin("I2C scan");
  i2cBegin();
  LOG.println(F("If the scan hangs or finds nothing at all: check SDA/SCL are not swapped,"));
  LOG.println(F("the sensors have 3V3 and GND, and the bus has pull-up resistors."));
}

void loop() {
  bool as5600 = false, tmp102 = false;
  uint8_t found = 0;
  LOG.println(F("\nScanning..."));
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      found++;
      LOG.print(F("  0x"));
      if (addr < 16) LOG.print('0');
      LOG.print(addr, HEX);
      LOG.print(F("  "));
      LOG.println(nameOf(addr));
      as5600 |= (addr == AS5600_I2C_ADDR);
      tmp102 |= (addr == TEMP_I2C_ADDR);
    }
  }
  if (!found) LOG.println(F("  nothing found"));
  printResult(as5600, F("AS5600 at 0x36"));
  printResult(tmp102, F("TMP102 at 0x48"));
  delay(5000);
}
