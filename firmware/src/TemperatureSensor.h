#pragma once
#include <Wire.h>
#include <stdint.h>

namespace uwsn {

/**
 * @brief Reads the air temperature from the sensor
 *
 * 12-bit, 0.0625 C per step, +-0.5 C accuracy between -25 and 85 C.
 *
 * To save battery the sensor is kept in shutdown mode (~1 uA) and each read()
 * triggers a single conversion ("one-shot"), so it only works when we ask for a value.
 */
class TemperatureSensor {
 public:
  /**
   * @param wire I2C bus of the sensor (shared with the AS5600)
   */
  explicit TemperatureSensor(TwoWire& wire = Wire);

  /**
   * @brief Checks the sensor answers and puts it in shutdown mode
   * @returns false if the sensor is not detected
   */
  bool begin();

  /**
   * @brief Starts one conversion, waits for it, reads the result
   * @param tempC the temperature to fill, in degrees C
   *
   * Blocks for TMP102_CONVERSION_MS (~35 ms), fine since it runs every TEMP_SAMPLE_EVERY_N seconds.
   *
   * @returns false if the sensor does not answer or gives an implausible value
   */
  bool read(float& tempC);

 private:
  /**
   * @brief Writes the 2-byte configuration register
   * @returns false on an I2C error
   */
  bool writeConfig(uint8_t msb, uint8_t lsb);

  /**
   * @brief Reads n consecutive registers starting at reg
   * @returns false on an I2C error
   */
  bool readRegs(uint8_t reg, uint8_t* buf, uint8_t n);

  TwoWire& wire_;
};

}  // namespace uwsn