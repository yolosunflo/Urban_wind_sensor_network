#include "Anemometer.h"
#include "config.h"
#include <Arduino.h>

namespace uwsn {

AnalogAnemometer::AnalogAnemometer(int s, int d, int p)
    : speedPin_(s), dirPin_(d), powerPin_(p) {}

bool AnalogAnemometer::begin() {
  pinMode(powerPin_, OUTPUT);
  analogReadResolution(ADC_BITS);
  return true;
}

void AnalogAnemometer::powerOn()  { digitalWrite(powerPin_, HIGH); delay(SENSOR_WARMUP_MS); }
void AnalogAnemometer::powerOff() { digitalWrite(powerPin_, LOW); }

bool AnalogAnemometer::read(RawSample& out) {
  out.speedAdc = analogRead(speedPin_);
  out.dirAdc   = analogRead(dirPin_);
  out.tMs      = millis();
  // TODO: detect disconnected sensor (ADC stuck at 0 or full scale) -> return false
  return true;
}

}  // namespace uwsn
