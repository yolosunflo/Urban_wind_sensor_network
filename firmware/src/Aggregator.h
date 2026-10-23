#pragma once
#include "types.h"

namespace uwsn {

// Accumulates 1 Hz samples and produces one WindAggregate per window.
// Uses running sums so no sample buffer is needed in RAM.
class Aggregator {
 public:
  void reset();
  void add(const WindSample& s);
  uint16_t count() const { return sample_count; }
  WindAggregate compute() const;   // TODO: 3-s gust (WMO) instead of max sample

 private:
  uint16_t sample_count = 0;
  // Welford for speed mean / variance
  float mean_ = 0, m2_ = 0;
  float maxSpeed_ = 0;
  // Vector average for direction (never average angles directly)
  float sumSin_ = 0, sumCos_ = 0;
  // Stuck-sensor detection
  float lastSpeed_ = -1; uint16_t sameCount_ = 0; uint16_t maxSame_ = 0;
};

}  // namespace uwsn
