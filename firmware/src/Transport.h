#pragma once
#include <stdint.h>
#include <stddef.h>

namespace uwsn {

// Abstract radio link. The rest of the firmware never touches LoRa directly,
// so we can swap LoRaWAN for LTE-M later for example.
class ITransport {
 public:
  virtual ~ITransport() = default;
  virtual bool begin() = 0;                                // join network
  virtual bool send(const uint8_t* data, size_t len) = 0;  // uplink
  virtual bool pollDownlink(uint8_t* buf, size_t& len) = 0; // e.g. new calibration, new interval
  virtual void sleep() = 0;
};

class LoRaWANTransport : public ITransport {
 public:
  bool begin() override;                 // TODO: OTAA join (DevEUI, AppEUI, AppKey)
  bool send(const uint8_t* data, size_t len) override;   // TODO: unconfirmed uplink, port 1
  bool pollDownlink(uint8_t* buf, size_t& len) override; // TODO
  void sleep() override;                 // TODO: radio to sleep mode
};

}  // namespace uwsn
