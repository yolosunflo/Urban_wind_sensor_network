// Test 3: temperature sensor (SparkFun SEN-13314 = TMP102), with the real driver.
// Prints the temperature every 2 s with the running min / max.
// Check: close to a reference thermometer (+-0.5 C), rises when you hold the sensor
// between two fingers, comes back down after.
#include "bringup.h"
#include "TemperatureSensor.h"

using namespace uwsn;

static TemperatureSensor sensor;
static float tMin = 1000, tMax = -1000;
static uint32_t fails = 0, reads = 0;

void setup() {
  bringupBegin("temperature sensor (TMP102)");
  i2cBegin();
  const bool ok = sensor.begin();
  printResult(ok, F("TMP102 answers at its I2C address"));
  if (!ok) LOG.println(F("-> run test_i2c first"));
  LOG.println(F("\n   temp (C)     min      max    failed reads"));
}

void loop() {
  float t;
  reads++;
  if (sensor.read(t)) {
    tMin = min(tMin, t);
    tMax = max(tMax, t);
    LOG.print(F("   "));
    LOG.print(t, 2);
    LOG.print(F("       "));
    LOG.print(tMin, 2);
    LOG.print(F("    "));
    LOG.print(tMax, 2);
  } else {
    fails++;
    LOG.print(F("   read failed (no answer, or outside "));
    LOG.print(TEMP_MIN_C, 0);
    LOG.print(F(" .. "));
    LOG.print(TEMP_MAX_C, 0);
    LOG.print(F(" C)"));
  }
  LOG.print(F("    "));
  LOG.print(fails);
  LOG.print('/');
  LOG.println(reads);
  delay(2000);
}
