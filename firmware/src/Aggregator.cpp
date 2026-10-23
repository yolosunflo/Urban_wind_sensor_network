#include "Aggregator.h"
#include "config.h"
#include <math.h>

namespace uwsn {

void Aggregator::reset() { *this = Aggregator(); }

void Aggregator::add(const WindSample& s) {
  sample_count++;
  const float d = s.speed_ms - mean_;
  mean_ += d / sample_count;
  m2_   += d * (s.speed_ms - mean_);
  if (s.speed_ms > maxSpeed_) maxSpeed_ = s.speed_ms;

  const float rad = s.dir_deg * (float)M_PI / 180.0f;
  sumSin_ += sinf(rad);
  sumCos_ += cosf(rad);

  if (s.speed_ms == lastSpeed_) { if (++sameCount_ > maxSame_) maxSame_ = sameCount_; }
  else sameCount_ = 0;
  lastSpeed_ = s.speed_ms;
}

WindAggregate Aggregator::compute() const {
  WindAggregate a{};
  a.nSamples     = sample_count;
  a.meanSpeed_ms = mean_;
  a.gust_ms      = maxSpeed_;
  a.stdSpeed_ms  = (sample_count > 1) ? sqrtf(m2_ / (sample_count - 1)) : 0.0f;
  float dir = atan2f(sumSin_, sumCos_) * 180.0f / (float)M_PI;
  if (dir < 0) dir += 360.0f;
  a.meanDir_deg  = dir;

  a.flags = Q_OK;
  if (sample_count < (BURST_S * 1000UL / SAMPLE_PERIOD_MS) * 0.8f) a.flags |= Q_FEW_SAMPLES;
  if (maxSpeed_ > SPEED_MAX_MS)                           a.flags |= Q_OUT_OF_RANGE;
  if (maxSame_ > 300)                                     a.flags |= Q_STUCK;  // TODO tune
  return a;
}

}  // namespace uwsn
