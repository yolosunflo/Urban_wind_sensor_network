#pragma once
#include "types.h"

namespace uwsn {

/**
 * @brief Parameters shared by every anemometer type.
 */
struct CommonCalibParams {
  float dirOffsetDeg = 0.0f;   // mounting orientation correction (added to the angle)
  float tempOffsetC  = 0.0f;   // added to the temperature reading (from reference comparison)
};

/**
 * @brief Converts a RawSample (sensor units) into a WindSample (m/s, deg)
 * 
 * One base class + one sub-class per anemometer type:
 *    - AnalogCalibration : sensor with two analog voltage outputs (speed + vane)
 *    - PulseCalibration  : our own anemometer, reed/Hall pulses + AS5600 angle
 */
class Calibration {
 public:
  virtual ~Calibration() = default;

  /**
   * @brief Converts one raw reading into physical values
   * @param raw the raw values to convert (meaning depends on the anemometer type)
   *
   * @returns a WindSample with speed in m/s and direction in degrees (0..360)
   */
  virtual WindSample apply(const RawSample& raw) const = 0;

  /**
   * @brief Adds the temperature offset correction
   * @param rawTempC the raw temperature to convert
   *
   * @returns the corrected temperature in degrees C
   */
  float applyTemp(float rawTempC) const;

 protected:
  /**
   * @brief Parameters common to all types (each sub-class stores its own)
   */
  virtual const CommonCalibParams& common() const = 0;

  /**
   * @brief Adds the mounting offset and wraps the angle into [0, 360)
   * @param rawDeg direction before offset correction, in degrees
   *
   * @returns the corrected direction in degrees
   */
  float correctDirection(float rawDeg) const;

 private:
  CommonCalibParams params_;
};


/**
 * @brief Parameters of an analog anemometer
 */
struct AnalogCalibParams : CommonCalibParams {
  float speedOffsetV = 0.0f;   // voltage output at 0 m/s
  float speedGain = 1.0f;   // m/s per volt
};

/**
 * @brief Anemometer with analog voltage outputs
 */
class AnalogCalibration : public Calibration {
 public:
  /**
   * @brief Replaces the parameters
   */
  void set(const AnalogCalibParams& p) { params_ = p; }

  /**
   * @brief Converts ADC counts to volts, then to m/s and degrees
   */
  WindSample apply(const RawSample& raw) const override;

 protected:
  const CommonCalibParams& common() const override { return params_; }

 private:
  AnalogCalibParams params_;
};


/**
 * @brief Parameters of the pulse + AS5600 anemometer
 */
struct PulseCalibParams : CommonCalibParams {
  float    speedGain          = 1.0f;   // m/s per Hz (pulses per second), found against a reference
  float    speedOffset_ms     = 0.0f;   // intercept, linked to the start-up speed (~0.2-0.5 m/s)
  uint16_t angleCountsPerTurn = 4096;   // AS5600: 12-bit angle, 0..4095
};

/**
 * @brief Calibration for our own anemometer (pulse counting + AS5600)
 */
class PulseCalibration : public Calibration {
 public:
  /**
   * @brief Replaces the parameters
   */
  void set(const PulseCalibParams& p) { params_ = p; }

  /**
   * @brief Converts pulses to a frequency, then to m/s; AS5600 counts to degrees
   */
  WindSample apply(const RawSample& raw) const override;

 protected:
  const CommonCalibParams& common() const override { return params_; }

 private:
  PulseCalibParams params_;
};

}  // namespace uwsn
