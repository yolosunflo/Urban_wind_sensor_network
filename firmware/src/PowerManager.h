#pragma once
#include <stdint.h>

namespace uwsn {

class PowerManager {
 public:
  void begin();
  float readBatteryV() const;             // via voltage divider
  bool  isLow() const;
  void  deepSleep(uint32_t ms);           // MCU deep sleep (RTC wake-up)
  // TODO: optional solar charge status
};

}  // namespace uwsn
