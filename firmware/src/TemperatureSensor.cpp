#include "TemperatureSensor.h"
#include "config.h"
#include <Arduino.h>

namespace uwsn {

AnalogTemperatureSensor::AnalogTemperatureSensor(int pin) : pin_(pin) {}

bool AnalogTemperatureSensor::begin() {
  pinMode(pin_, INPUT);
  analogReadResolution(ADC_BITS);
  return true;
}

bool AnalogTemperatureSensor::read(float& tempC) {
  const float full = (1 << ADC_BITS) - 1;
  float sum = 0;
  for (int i = 0; i < 8; i++) sum += analogRead(pin_);   // averaging reduces ADC noise
  const float v = (sum / 8.0f) * ADC_VREF / full;
  tempC = (v - TEMP_V_AT_0C) / TEMP_V_PER_C;
  // Outside the plausible range = disconnected or shorted sensor
  return tempC > TEMP_MIN_C && tempC < TEMP_MAX_C;
}

}  // namespace uwsn
