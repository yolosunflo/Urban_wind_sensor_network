// Test 1: the board alone (nothing else connected except the antenna, see docs/testing.md).
// Checks: the program runs, the serial monitor works, the supply voltage is right,
// and deep sleep wakes up again (needed by the real firmware).
#include "bringup.h"
#include <STM32LowPower.h>

static uint32_t cycle = 0;

static float supplyVoltage() {
  // The chip compares its internal 1.2 V reference with its supply: no wiring needed
  analogReadResolution(12);
  const uint32_t raw = analogRead(AVREF);
  return __LL_ADC_CALC_VREFANALOG_VOLTAGE(raw, LL_ADC_RESOLUTION_12B) / 1000.0f;
}

void setup() {
  bringupBegin("board alone");
  LowPower.begin();

  const float v = supplyVoltage();
  LOG.print(F("Supply voltage (VDD): "));
  LOG.print(v, 2);
  LOG.println(F(" V   (expected 3.2 - 3.4 V)"));
  printResult(v > 3.1f && v < 3.5f, F("supply voltage"));
  LOG.print(F("CPU clock: "));
  LOG.print(SystemCoreClock / 1000000);
  LOG.println(F(" MHz"));
  LOG.println(F("Now alternating 2 s awake / 5 s deep sleep. If the counter keeps going up,"));
  LOG.println(F("deep sleep works. (The serial line may print garbage for a moment after wake-up.)"));
}

void loop() {
  LOG.print(F("cycle "));
  LOG.print(++cycle);
  LOG.print(F("  awake, millis() = "));
  LOG.println(millis());
  delay(2000);
  LOG.println(F("  going to deep sleep for 5 s..."));
  LOG.flush();
  LowPower.deepSleep(5000);
  if (cycle == 3) printResult(true, F("woke up from deep sleep 3 times"));
}
