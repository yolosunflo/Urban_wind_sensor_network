#pragma once
#include "types.h"
#include "Calibration.h"
#include <stddef.h>

namespace uwsn {

/**
 * @brief Converts float aggregates <-> fixed-point frame <-> bytes (big-endian),
 * and decodes the calibration downlinks.
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
   * Clamping so nothing overflows.
   *
   * @returns the same structure but with integer values only
   */
  static UplinkFrame toFrame(const WindAggregate& a, uint16_t seq, float batteryV);

  /**
   * @brief encodes an structure of data UplinkFrame into one 14 bytes message (big-endian)
   *
   * @param f the data we want to encode
   * @param buf the buffer that will contain the final message
   *
   * @returns the number of bytes written
   */
  static size_t encode(const UplinkFrame& f, uint8_t* buf);

  /**
   * @brief decode a 14 bytes message into an UplinkFrame
   * @returns false if len of the buffer < to UPLINK_SIZE
   *
   * @note only for unit tests, it won't be used in the protocol
   */
  static bool decode(const uint8_t* buf, size_t len, UplinkFrame& out); // for unit tests

  /**
   * @brief Applies a calibration downlink (port DOWNLINK_PORT) to a set of parameters
   * @param buf, len the downlink payload
   * @param p in: the current parameters, out: the new ones (fields not in the command,
   *          like angleCountsPerTurn, are kept)
   *
   * @returns false if the command is unknown, too short or invalid (p is then unchanged)
   */
  static bool decodeCalibration(const uint8_t* buf, size_t len, PulseCalibParams& p);
};

}  // namespace uwsn
