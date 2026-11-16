// Test 6: battery voltage measurement (divider on PB3), with the real PowerManager.
// Prints every 2 s the raw ADC value and the computed battery voltage.
// Check with a multimeter on the battery: the two values must agree within ~0.05 V.
// If they don't, measure the two resistors and correct BATTERY_DIVIDER in config.h.
#include "bringup.h"
#include "PowerManager.h"

using namespace uwsn;

static PowerManager power;

void setup() {
  bringupBegin("battery voltage");
  power.begin();
  LOG.print(F("BATTERY_DIVIDER = "));
  LOG.print(BATTERY_DIVIDER, 3);
  LOG.print(F(", low battery below "));
  LOG.print(LOW_BATTERY_V, 2);
  LOG.println(F(" V"));
  LOG.println(F("With no divider wired the value floats: that is expected, not a bug."));
  LOG.println(F("\n raw ADC   battery (V)   low?"));
}

void loop() {
  const int raw = analogRead(PIN_BATTERY_ADC);
  const float v = power.readBatteryV();
  LOG.print(F("  "));
  LOG.print(raw);
  LOG.print(F("      "));
  LOG.print(v, 3);
  LOG.print(F("        "));
  LOG.println(power.isLow() ? F("LOW") : F("ok"));
  delay(2000);
}
