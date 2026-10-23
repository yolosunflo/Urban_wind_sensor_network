#include "PowerManager.h"
#include "config.h"
#include <Arduino.h>

namespace uwsn {

void PowerManager::begin() { pinMode(PIN_BATTERY_ADC, INPUT); }

float PowerManager::readBatteryV() const {
  const float full = (1 << ADC_BITS) - 1;
  return analogRead(PIN_BATTERY_ADC) * ADC_VREF / full * BATTERY_DIVIDER;
}

bool PowerManager::isLow() const { return readBatteryV() < LOW_BATTERY_V; }

void PowerManager::deepSleep(uint32_t ms) {
  // TODO: board-specific (esp_deep_sleep_start / STM32 STOP mode)
  delay(ms);
}

}  // namespace uwsn
