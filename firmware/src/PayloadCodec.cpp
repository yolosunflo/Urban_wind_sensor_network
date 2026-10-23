#include "PayloadCodec.h"
#include "config.h"
#include <math.h>
#include <limits.h>

namespace uwsn {

static uint16_t clampU16(float v) { return v < 0 ? 0 : (v > 65535.f ? 65535 : (uint16_t)lroundf(v)); }
static uint8_t  clampU8 (float v) { return v < 0 ? 0 : (v > 255.f   ? 255   : (uint8_t) lroundf(v)); }

UplinkFrame PayloadCodec::toFrame(const WindAggregate& a, uint16_t seq,
                                  float batteryV, bool hasTemp, float tempC) {
  UplinkFrame f{};
  f.version  = PAYLOAD_VERSION;
  f.seq      = seq;
  f.meanSpeed= clampU16(a.meanSpeed_ms / SPEED_LSB_MS);
  f.gust     = clampU16(a.gust_ms      / SPEED_LSB_MS);
  f.meanDir  = clampU16(a.meanDir_deg  / DIR_LSB_DEG);
  f.stdSpeed = clampU8 (a.stdSpeed_ms  / STD_LSB_MS);
  f.temp     = hasTemp ? (int16_t)lroundf(tempC / TEMP_LSB_C) : INT16_MIN;
  f.battery  = clampU8 ((batteryV - BATTERY_OFFSET_V) / BATTERY_LSB_V);
  f.flags    = a.flags;
  return f;
}

static void put16(uint8_t* p, uint16_t v) { p[0] = v >> 8; p[1] = v & 0xFF; }
static uint16_t get16(const uint8_t* p)   { return (uint16_t)(p[0] << 8 | p[1]); }

size_t PayloadCodec::encode(const UplinkFrame& f, uint8_t* b, size_t cap) {
  if (cap < UPLINK_SIZE) return 0;
  b[0] = f.version;
  put16(b + 1,  f.seq);
  put16(b + 3,  f.meanSpeed);
  put16(b + 5,  f.gust);
  put16(b + 7,  f.meanDir);
  b[9] = f.stdSpeed;
  put16(b + 10, (uint16_t)f.temp);
  b[12] = f.battery;
  b[13] = f.flags;
  return UPLINK_SIZE;
}

bool PayloadCodec::decode(const uint8_t* b, size_t len, UplinkFrame& f) {
  if (len < UPLINK_SIZE) return false;
  f.version = b[0];  f.seq = get16(b + 1);
  f.meanSpeed = get16(b + 3); f.gust = get16(b + 5); f.meanDir = get16(b + 7);
  f.stdSpeed = b[9]; f.temp = (int16_t)get16(b + 10);
  f.battery = b[12]; f.flags = b[13];
  return true;
}

}  // namespace uwsn
