#include "Aggregator.h"
#include "config.h"
#include <math.h>

namespace uwsn {

// Maximum nb of identical values (stuck)
#define SAME_VAL_DETECT 300 // TODO tdb
#define TO_MS 1000UL
#define EXP_SAMPLE 0.8f // expect 80% of good samples

/**
 * Helper functions
 */
static float rad_to_deg(float x) {return x * 180.0f / (float)M_PI;}
static float deg_to_rad(float x) {return x * (float)M_PI / 180.0f;}

void Aggregator::reset() { *this = Aggregator(); }

void Aggregator::addTemp(float tempC) {
  if (tempC < TEMP_MIN_C || tempC > TEMP_MAX_C) {tBad_++; return;}
  tSum_ += tempC;
  tGood_++;
}

void Aggregator::add(const WindSample& s) {
  sample_count++;
  const float d = s.speed_ms - mean_;
  mean_ += d / sample_count;
  m2_   += d * (s.speed_ms - mean_);
  if (s.speed_ms > maxSpeed_) maxSpeed_ = s.speed_ms;

  const float rad = deg_to_rad(s.dir_deg);
  sumSin_ += sinf(rad);
  sumCos_ += cosf(rad);

  sameCount_ = s.speed_ms == lastSpeed_ ? sameCount_++ : 0;
  lastSpeed_ = s.speed_ms;
}

WindAggregate Aggregator::compute() const {
  WindAggregate a{};
  a.meanSpeed_ms = mean_;
  a.gust_ms = maxSpeed_;

  float dir = rad_to_deg(atan2f(sumSin_, sumCos_));
  a.meanDir_deg  = dir < 0 ? dir + 360.0f : dir;

  a.stdSpeed_ms = (sample_count > 1) ? sqrtf(m2_ / (sample_count - 1)) : 0.0f;

  a.hasTemp = (tGood_ > 0);
  a.meanTemp_c = a.hasTemp ? tSum_ / tGood_ : 0.0f;
  if (!a.hasTemp || tBad_ > tGood_) a.flags |= Q_TEMP_FAULT;

  a.nSamples = sample_count;

  a.flags = Q_OK;
  if (sample_count < (BURST_S * TO_MS / SAMPLE_PERIOD_MS) * EXP_SAMPLE) a.flags |= Q_FEW_SAMPLES;
  if (maxSpeed_ > SPEED_MAX_MS) a.flags |= Q_OUT_OF_RANGE;
  if (sameCount_ > SAME_VAL_DETECT) a.flags |= Q_STUCK;

  return a;
}

}  // namespace uwsn
