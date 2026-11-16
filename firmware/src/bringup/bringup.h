#pragma once
// Shared by the hardware tests in this folder (see docs/testing.md).
// Each test is a small program of its own: flash it with  pio run -e <test> -t upload
// and read it with  pio device monitor.
#include <Arduino.h>
#include <Wire.h>
#include "config.h"

// If nothing appears in the serial monitor, the USB-C port may be wired to another UART
// on your board version: replace Serial by Serial1 here.
#define LOG Serial

inline void bringupBegin(const char* name) {
  LOG.begin(115200);
  const uint32_t t0 = millis();
  while (!LOG && millis() - t0 < 3000) {}        // give the monitor time to open
  delay(500);
  LOG.println();
  LOG.println(F("=================================================="));
  LOG.print(F("  UWSN hardware test: "));
  LOG.println(name);
  LOG.println(F("=================================================="));
}

inline void i2cBegin() {
  Wire.setSDA(PIN_I2C_SDA);
  Wire.setSCL(PIN_I2C_SCL);
  Wire.begin();
}

inline void printResult(bool ok, const __FlashStringHelper* what) {
  LOG.print(ok ? F("[ OK ]   ") : F("[FAIL]   "));
  LOG.println(what);
}
