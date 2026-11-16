#pragma once
#include <stdint.h>
#include <stddef.h>

namespace uwsn {

/**
 * @brief LoRaWAN link (RadioLib, built-in radio of the STM32WLE5JC), class A, OTAA join
 *
 * Class A: the node can only receive right after it sends. So send() also listens for a
 * downlink and keeps it; pollDownlink() hands it over afterwards.
 * Keys are in secrets.h (copy secrets.example.h, never commit the real one).
 */
class LoRaWANTransport {
 public:
  /**
   * @brief Starts the radio and joins the network (OTAA)
   * @returns false if the join failed (send() retries it)
   */
  bool begin();

  /**
   * @brief Sends one unconfirmed uplink on UPLINK_PORT, then listens for a downlink
   * @returns false if not joined or the radio failed
   */
  bool send(const uint8_t* data, size_t len);

  /**
   * @brief Gives the downlink received during the last send(), if any, on DOWNLINK_PORT
   * @param buf at least DOWNLINK_MAX_SIZE bytes
   * @returns true once per downlink
   */
  bool pollDownlink(uint8_t* buf, size_t& len);

  /**
   * @brief Puts the radio to sleep
   */
  void sleep();

 private:
  bool join();
  bool joined_ = false;
};

}  // namespace uwsn
