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
   * @param s the sample to add
   * 
   * Updates all the variables of the class
   */
  void add(const WindSample& s);

  /**
   * @brief add a temperature data to the accumulated data.
   * @param tempC the temperature to add
   * 
   * It rejects implausible values
   * Temperature is sampled less often than wind
   */
  void addTemp(float tempC);

  /**
   * @brief Gives the number of samples in the current accumulated data
   * @returns the number of samples
   */
  uint16_t count() const { return sample_count; }

  /**
   * @brief Create the final wind aggregate from the data accumulated
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
  float lastSpeed_ = -1; uint16_t sameCount_ = 0;  // Stuck-sensor detection
};

}  // namespace uwsn
