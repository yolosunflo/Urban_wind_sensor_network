#include "PowerManager.h"
#include "config.h"
#include <Arduino.h>
#include <STM32LowPower.h>

namespace uwsn {

void PowerManager::begin() {
  pinMode(PIN_BATTERY_ADC, INPUT_ANALOG);
  analogReadResolution(ADC_BITS);
  LowPower.begin();
}

float PowerManager::readBatteryV() const {
  uint32_t sum = 0;
  for (int i = 0; i < BATTERY_ADC_AVG; i++) sum += analogRead(PIN_BATTERY_ADC);
  const float full = (1 << ADC_BITS) - 1;
  return (sum / (float)BATTERY_ADC_AVG) * ADC_VREF / full * BATTERY_DIVIDER;
}

bool PowerManager::isLow() const { return readBatteryV() < LOW_BATTERY_V; }

void PowerManager::deepSleep(uint32_t ms) { LowPower.deepSleep(ms); }

}  // namespace uwsn
