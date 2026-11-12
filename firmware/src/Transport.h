#pragma once
#include <stdint.h>
#include <stddef.h>

namespace uwsn {

/**
 * @brief Radio link using LoRaWAN
 */
class LoRaWANTransport {
 public:
  ~LoRaWANTransport() = default;
  /**
   * @brief join the network
   * @todo implement
   */
  bool begin();

  /**
   * @brief send the data over LoRaWAN
   * @todo implement. unconfirmed uplink, port 1 ??
   */
  bool send(const uint8_t* data, size_t len);

  /**
   * @brief check whether the server sent us something (new calibration, new interval).
   * @todo implement
   */
  bool pollDownlink(uint8_t* buf, size_t& len);

  /**
   * @brief put the radio to sleep
   * @todo implement
   */
  void sleep();
};

}  // namespace uwsn
