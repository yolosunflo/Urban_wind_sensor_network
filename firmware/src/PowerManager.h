#pragma once
#include <stdint.h>

namespace uwsn {

/**
 * @brief Battery voltage and deep sleep (LoRa-E5 mini, STM32duino + STM32LowPower)
 *
 * The battery is read through a voltage divider on PIN_BATTERY_ADC (not on the board:
 * two resistors to add, see config.h).
 */
class PowerManager {
 public:
  /**
   * @brief Initialise the battery reader and the low-power library
   */
  void begin();

  /**
   * @brief Measure the battery voltage
   * @returns the current voltage of the battery
   */
  float readBatteryV() const;

  /**
   * @returns true if the battery is below LOW_BATTERY_V
   */
  bool isLow() const;

  /**
   * @brief Put the microcontroller in STOP2 mode for a given time (woken by the RTC)
   * @param ms the duration of the sleep
   *
   * RAM is kept (variables, LoRaWAN session), millis() does not advance meanwhile.
   */
  void deepSleep(uint32_t ms);
};

}  // namespace uwsn
