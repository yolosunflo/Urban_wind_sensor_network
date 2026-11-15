#pragma once
#include "types.h"

namespace uwsn {

/**
 * @brief Accumulates 1 Hz samples and produces one WindAggregate per window.
 * 
 * @note Uses running sums so no sample buffer is needed in RAM.
 */
class Aggregator {
 public:
  /**
   * @brief Reset the value accumulated to start a new aggregate
   */
  void reset();

  /**
   * @brief Add one sample to the current data
   * Updates all the variables of the class
   */
  void add(const WindSample& s);

  /**
   * @brief Adds one valid temperature reading (already checked by TemperatureSensor)
   */
  void addTemp(float tempC);

  /**
   * @brief Counts one failed temperature reading (implausible value or no answer)
   */
  void addTempFault() { tBad_++; }

  /**
   * @brief Gives the number of samples in the current accumulated data
   * @returns the number of samples
   */
  uint16_t count() const { return sample_count; }

  /**
   * @brief Create the final wind aggregate from the data accumulated
   * Sets the quality flags
   * 
   * Called only once at the end of the receiving window
   */
  WindAggregate compute() const;

 private:
  uint16_t sample_count = 0;
  float mean_ = 0, m2_ = 0;                        // Welford for speed mean/variance
  float maxSpeed_ = 0, tSum_ = 0;
  float sumSin_ = 0, sumCos_ = 0;                  // Vector average for direction
  uint16_t tGood_ = 0, tBad_ = 0;                  // nb of good/bad temperature data
  
  // Stuck sensor detection
  float lastDir_ = -1;        // previous direction, -1 = no sample yet
  uint16_t vaneStill_ = 0;    // windy samples in a row where the vane did not move
  uint16_t vaneMoves_ = 0;    // samples in this window where the vane moved
  
};

}  // namespace uwsn
