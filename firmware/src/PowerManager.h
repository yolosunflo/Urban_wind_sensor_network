#pragma once
#include <stdint.h>

namespace uwsn {

/**
 * @brief Handles the power consumption of the module
 * 
 * @todo DEPENDS A LOT ON OUR COMPONENTS -> WILL NEED TO BE UPDATED
 */
class PowerManager {
 public:
  /**
   * @brief Initialise the battery reader
   */
  void begin();

  /**
   * @brief Measure the battery voltage
   * @returns the current voltage of the battery
   * 
   * @note depends on our architecture : BATTERY_DIVIDER = (R1 + R2) / R2
   */
  float readBatteryV() const;

  /**
   * @returns true if the battery is low (below a threshold *TBD*)
   */
  bool isLow() const;

  /**
   * @brief Put the microcontroller to sleep for a given time (board specific, TODO)
   * @param ms the duration of the sleep
   */
  void deepSleep(uint32_t ms);
};

}  // namespace uwsn
