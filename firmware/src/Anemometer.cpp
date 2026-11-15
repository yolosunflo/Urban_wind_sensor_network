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


#include "Anemometer.h"
#include "config.h"
#include <Arduino.h>

#ifndef IRAM_ATTR          // ESP32 needs ISRs in RAM, other boards (STM32WL) ignore it
#define IRAM_ATTR
#endif

namespace uwsn {

// Analog anemometer

AnalogAnemometer::AnalogAnemometer(int s, int d, int p)
    : speedPin_(s), dirPin_(d), powerPin_(p) {}

bool AnalogAnemometer::begin() {
  pinMode(speedPin_, INPUT);
  pinMode(dirPin_, INPUT);
  if (powerPin_ != NO_PIN) {
    pinMode(powerPin_, OUTPUT);
    digitalWrite(powerPin_, LOW);
  }
  analogReadResolution(ADC_BITS);
  return true;   // an analog sensor cannot be "detected", faults are caught in read()
}

void AnalogAnemometer::powerOn() {
  if (powerPin_ != NO_PIN) digitalWrite(powerPin_, HIGH);
  delay(SENSOR_WARMUP_MS);
}

void AnalogAnemometer::powerOff() {
  if (powerPin_ != NO_PIN) digitalWrite(powerPin_, LOW);
}

uint16_t AnalogAnemometer::readAveraged(int pin) const {
  uint32_t sum = 0;
  for (int i = 0; i < ANEMO_ADC_AVG; i++) sum += analogRead(pin);
  return sum / ANEMO_ADC_AVG;
}

bool AnalogAnemometer::read(RawSample& out) {
  out = RawSample{};
  out.speedAdc = readAveraged(speedPin_);
  out.dirAdc   = readAveraged(dirPin_);

  // Stuck at full scale = open wire or sensor not powered.
  // (0 is not checked: it is a valid value, 0 m/s or vane pointing at 0 deg.)
  const uint16_t full = (1 << ADC_BITS) - 1;
  if (out.speedAdc >= full - ANEMO_ADC_RAIL_MARGIN) return false;
  if (out.dirAdc   >= full - ANEMO_ADC_RAIL_MARGIN) return false;
  return true;
}


// Our own anemometer (reed switch + AS5600)

// AS5600 registers (datasheet), fixed by the chip so not in config.h
constexpr uint8_t AS5600_REG_STATUS = 0x0B;
constexpr uint8_t AS5600_REG_RAW_ANGLE = 0x0C;
constexpr uint8_t AS5600_STATUS_MD = 1 << 5; // magnet detected

volatile uint16_t PulseAnemometer::pulseCount_  = 0;
volatile uint32_t PulseAnemometer::lastPulseUs_ = 0;

PulseAnemometer::PulseAnemometer(int reedPin, int powerPin, TwoWire& wire)
    : reedPin_(reedPin), powerPin_(powerPin), wire_(wire) {}

bool PulseAnemometer::begin() {
  pinMode(reedPin_, INPUT);   // pull-up only enabled while sampling, see powerOn()
  wire_.begin();

  // Check the AS5600 answers (power it briefly if it is gated)
  if (powerPin_ != NO_PIN) {
    pinMode(powerPin_, OUTPUT);
    digitalWrite(powerPin_, HIGH);
    delay(AS5600_STARTUP_MS);
  }
  wire_.beginTransmission(AS5600_I2C_ADDR);
  const bool found = (wire_.endTransmission() == 0);
  if (powerPin_ != NO_PIN) digitalWrite(powerPin_, LOW);
  return found;
}

void PulseAnemometer::powerOn() {
  if (powerPin_ != NO_PIN) {
    digitalWrite(powerPin_, HIGH);
    delay(AS5600_STARTUP_MS);
  }
  pinMode(reedPin_, INPUT_PULLUP);
  noInterrupts();
  pulseCount_  = 0;
  lastPulseUs_ = micros();
  interrupts();
  lastReadMs_ = millis();
  attachInterrupt(digitalPinToInterrupt(reedPin_), onPulse, FALLING);
}

void PulseAnemometer::powerOff() {
  detachInterrupt(digitalPinToInterrupt(reedPin_));
  pinMode(reedPin_, INPUT);
  if (powerPin_ != NO_PIN) digitalWrite(powerPin_, LOW);
}

void IRAM_ATTR PulseAnemometer::onPulse() {
  const uint32_t now = micros();
  if (now - lastPulseUs_ < REED_DEBOUNCE_US) return;   // contact bounce
  lastPulseUs_ = now;
  pulseCount_++;
}

bool PulseAnemometer::read(RawSample& out) {
  out = RawSample{};

  // Take the pulse count and reset it in one go so no pulse is lost or counted twice
  const uint32_t now = millis();
  noInterrupts();
  out.pulses  = pulseCount_;
  pulseCount_ = 0;
  interrupts();
  out.dtMs    = now - lastReadMs_;
  lastReadMs_ = now;

  return readAngle(out.angleRaw);
}

bool PulseAnemometer::readAngle(uint16_t& angle) {
  uint8_t status;
  if (!readRegs(AS5600_REG_STATUS, &status, 1)) return false;   // chip not answering
  if (!(status & AS5600_STATUS_MD)) return false;               // magnet missing / fell off

  uint8_t b[2];
  if (!readRegs(AS5600_REG_RAW_ANGLE, b, 2)) return false;
  angle = ((b[0] & 0x0F) << 8) | b[1];
  return true;
}

bool PulseAnemometer::readRegs(uint8_t reg, uint8_t* buf, uint8_t n) {
  wire_.beginTransmission(AS5600_I2C_ADDR);
  wire_.write(reg);
  if (wire_.endTransmission(false) != 0) return false;   // repeated start, keep the bus
  if (wire_.requestFrom((uint8_t)AS5600_I2C_ADDR, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = wire_.read();
  return true;
}

}  // namespace uwsn