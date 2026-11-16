#pragma once
#include <Wire.h>
#include "types.h"

namespace uwsn {

/**
 * @brief Reads one raw sample from the anemometer (sensor units, no conversion)
 *
 * One base class + one sub-class per anemometer type, matching Calibration:
 *    - AnalogAnemometer: sensor with two analog voltage outputs (speed + vane) -> AnalogCalibration
 *      (kept for reference, not used on our node)
 *    - PulseAnemometer: our own anemometer, reed switch pulses + AS5600 angle -> PulseCalibration
 *
 * The type used by the node is chosen with ANEMOMETER_TYPE in config.h.
 */
class Anemometer {
 public:
  virtual ~Anemometer() = default;

  /**
   * @brief Initialise the pins/bus and check the sensor answers
   * @returns false if the sensor is not detected
   */
  virtual bool begin() = 0;

  /**
   * @brief Take one reading
   * @param out the raw sample to fill (only the fields of this anemometer type are set, the others are 0)
   *
   * @returns false if the sensor looks disconnected or broken (the sample must be ignored)
   */
  virtual bool read(RawSample& out) = 0;

  /**
   * @brief Switch the sensor on before a sampling burst (includes the warm-up delay)
   */
  virtual void powerOn() = 0;

  /**
   * @brief Switch the sensor off after a sampling burst to save battery
   */
  virtual void powerOff() = 0;

  static constexpr int NO_PIN = -1;   // use as power pin when the sensor is not power-gated
};


/**
 * @brief Anemometer with analog voltage outputs (voltage proportional to speed, potentiometer vane)
 */
class AnalogAnemometer : public Anemometer {
 public:
  /**
   * @param speedPin ADC pin of the speed output
   * @param dirPin   ADC pin of the vane output
   * @param powerPin pin driving the MOSFET that powers the sensor
   */
  AnalogAnemometer(int speedPin, int dirPin, int powerPin = NO_PIN);

  bool begin() override;

  /**
   * @brief Averages ANEMO_ADC_AVG readings per channel to reduce ADC noise
   *
   * @returns false if a channel is stuck at full scale (open wire / sensor unpowered)
   */
  bool read(RawSample& out) override;

  void powerOn() override;
  void powerOff() override;

 private:
  /**
   * @brief Average of ANEMO_ADC_AVG analogRead() on one pin
   */
  uint16_t readAveraged(int pin) const;

  int speedPin_, dirPin_, powerPin_;
};


/**
 * @brief Our own anemometer: reed switch for speed, AS5600 magnetic angle sensor for direction
 *
 * Speed: the reed switch closes once per magnet pass and pulls the GPIO to GND (internal
 * pull-up).
 *
 * @note The pulse counter is static (an interrupt cannot call a member function), so only
 * one PulseAnemometer can exist per node, which is our case.
 */
class PulseAnemometer : public Anemometer {
 public:
  /**
   * @param reedPin GPIO of the reed switch (other side of the switch on GND)
   * @param powerPin pin powering the AS5600 (NO_PIN if on the 3V3 rail, as on our schematic)
   * @param wire I2C bus of the AS5600 (shared with the TMP102 temperature sensor)
   */
  explicit PulseAnemometer(int reedPin, int powerPin = NO_PIN, TwoWire& wire = Wire);

  /**
   * @brief Configures the reed pin and the I2C bus, checks the AS5600 answers
   */
  bool begin() override;

  /**
   * @brief Takes the pulses counted since the last call and reads the AS5600 angle
   *
   * @returns false if the AS5600 does not answer or detects no magnet
   * (out.pulses is still filled, but main.cpp drops the whole sample)
   */
  bool read(RawSample& out) override;

  /**
   * @brief Powers the AS5600 if gated, resets the counter and starts counting pulses
   */
  void powerOn() override;

  /**
   * @brief Stops counting and releases the pull-up (a reed switch stopped closed
   * on the magnet would otherwise drain current through it during sleep)
   */
  void powerOff() override;

 private:
  /**
   * @brief Interrupt routine: counts one pulse, ignores bounces shorter than REED_DEBOUNCE_US
   */
  static void onPulse();

  /**
   * @brief Reads the AS5600 raw angle
   * @param angle the angle 0..4095 to fill
   *
   * @returns false if the chip does not answer or no magnet is detected
   */
  bool readAngle(uint16_t& angle);

  /**
   * @brief Reads n consecutive AS5600 registers starting at reg
   * @returns false on an I2C error
   */
  bool readRegs(uint8_t reg, uint8_t* buf, uint8_t n);

  int reedPin_, powerPin_;
  TwoWire& wire_;
  uint32_t lastReadMs_ = 0;                  // time of the previous read(), for dtMs

  static volatile uint16_t pulseCount_;      // pulses since the previous read()
  static volatile uint32_t lastPulseUs_;     // for debouncing
};

}  // namespace uwsn
