#include "Aggregator.h"
#include "config.h"
#include <math.h>

namespace uwsn {

#define EXP_SAMPLE 0.8f // expect 80% of good samples

/**
 * Helper functions
 */
static float rad_to_deg(float x) {return x * 180.0f / (float)M_PI;}
static float deg_to_rad(float x) {return x * (float)M_PI / 180.0f;}

void Aggregator::reset() { *this = Aggregator(); }

void Aggregator::addTemp(float tempC) {
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

  // Stuck detection: the cups (speed) and the vane (angle) check each other
  if (lastDir_ >= 0) {
    float dDir = fabsf(s.dir_deg - lastDir_);
    if (dDir > 180.0f) dDir = 360.0f - dDir;   // 359 -> 1 deg is a 2 deg move, not 358
    if (dDir > STUCK_DIR_TOL_DEG) { vaneMoves_++; vaneStill_ = 0; }
    else if (s.speed_ms > STUCK_MIN_SPEED_MS) vaneStill_++;
    // calm + vane still is normal: leave the counter as it is
  }
  lastDir_ = s.dir_deg;
}

WindAggregate Aggregator::compute() const {
  WindAggregate a{};
  a.meanSpeed_ms = mean_;
  a.gust_ms = maxSpeed_;

  float dir = rad_to_deg(atan2f(sumSin_, sumCos_));
  a.meanDir_deg  = dir < 0 ? dir + 360.0f : dir;

  a.stdSpeed_ms = (sample_count > 1) ? sqrtf(m2_ / (sample_count - 1)) : 0.0f;

  a.nSamples = sample_count;

  a.flags = Q_OK;
  if (sample_count < (BURST_S * 1000UL / SAMPLE_PERIOD_MS) * EXP_SAMPLE) a.flags |= Q_FEW_SAMPLES;
  if (maxSpeed_ > SPEED_MAX_MS) a.flags |= Q_OUT_OF_RANGE;
  if (vaneStill_ > STUCK_VANE_N) a.flags |= Q_STUCK;                       // wind, but the vane is frozen
  if (maxSpeed_ == 0.0f && vaneMoves_ > STUCK_CUPS_MOVES) a.flags |= Q_STUCK; // vane moves, but not one pulse

  a.hasTemp = (tGood_ > 0);
  a.meanTemp_c = a.hasTemp ? tSum_ / tGood_ : 0.0f;
  if (!a.hasTemp || tBad_ > tGood_) a.flags |= Q_TEMP_FAULT;

  return a;
}

}  // namespace uwsn
