#include "PowerManager.h"
#include "config.h"
#include <Arduino.h>

namespace uwsn {

void PowerManager::begin() { pinMode(PIN_BATTERY_ADC, INPUT); }

float PowerManager::readBatteryV() const { return 4.f; }

bool PowerManager::isLow() const { return readBatteryV() < LOW_BATTERY_V; }

void PowerManager::deepSleep(uint32_t ms) {}

}  // namespace uwsn
