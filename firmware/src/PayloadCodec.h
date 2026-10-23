#pragma once
#include "types.h"
#include <stddef.h>

namespace uwsn {

// Converts float aggregates <-> fixed-point frame <-> bytes (big-endian).
class PayloadCodec {
 public:
  static UplinkFrame toFrame(const WindAggregate& a, uint16_t seq,
                             float batteryV, bool hasTemp, float tempC);
  static size_t encode(const UplinkFrame& f, uint8_t* buf, size_t cap);  // returns bytes written, 0 on error
  static bool   decode(const uint8_t* buf, size_t len, UplinkFrame& out); // for unit tests
};

}  // namespace uwsn
