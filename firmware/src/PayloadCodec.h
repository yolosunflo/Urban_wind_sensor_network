#pragma once
#include "types.h"
#include <stddef.h>

namespace uwsn {

/**
 * Converts float aggregates <-> fixed-point frame <-> bytes (big-endian).
 */
class PayloadCodec {
public:
  /**
   * @brief converts an aggregation window of wind data into fixed-point integer values
   * 
   * @param a wind data
   * @param seq message counter used by the server to detect lost packets
   * @param batteryV battery of the module
   * 
   * @returns the same structure but with integer values only
   */
  static UplinkFrame toFrame(const WindAggregate& a, uint16_t seq, float batteryV);

  /**
   * @brief encodes an structure of data UplinkFrame into one bytes message
   * 
   * @param f the data we want to encode
   * @param buf the buffer that will contain the final message
   * 
   * @returns the number of bytes written
   */
  static size_t encode(const UplinkFrame& f, uint8_t* buf);

  /**
   * @brief decode a bytes message into an UplinkFrame
   * @returns false if len of the buffer < to UPLINK_SIZE
   * @note only for unit tests, it won't be used in the protocol
   */
  static bool decode(const uint8_t* buf, size_t len, UplinkFrame& out); // for unit tests
};

}  // namespace uwsn
