#include "Transport.h"
#include "config.h"
#include "secrets.h"     // JOIN_EUI, DEV_EUI, APP_KEY, NWK_KEY (from the TTN console)
#include <Arduino.h>
#include <RadioLib.h>
#include <string.h>

// Written for RadioLib 7.x. If a name does not compile, compare with the library's
// examples/LoRaWAN/LoRaWAN_Starter and examples/STM32WLx.

namespace uwsn {

namespace {
STM32WLx radio = new STM32WLx_Module();

// LoRa-E5 RF switch: receive = PA4 high, transmit (high-power output only) = PA5 high
const uint32_t rfswitchPins[] = {PA4, PA5, RADIOLIB_NC, RADIOLIB_NC, RADIOLIB_NC};
const Module::RfSwitchMode_t rfswitchTable[] = {
  {STM32WLx::MODE_IDLE,  {LOW,  LOW}},
  {STM32WLx::MODE_RX,    {HIGH, LOW}},
  {STM32WLx::MODE_TX_HP, {LOW,  HIGH}},
  END_OF_MODE_TABLE,
};

LoRaWANNode node(&radio, &EU868);

uint8_t dlBuf[256];          // LoRaWAN maximum payload, RadioLib writes the whole downlink here
size_t  dlLen = 0;
bool    dlPending = false;
}  // namespace

bool LoRaWANTransport::begin() {
  radio.setRfSwitchTable(rfswitchPins, rfswitchTable);
  if (radio.begin() != RADIOLIB_ERR_NONE) return false;
  if (node.beginOTAA(JOIN_EUI, DEV_EUI, NWK_KEY, APP_KEY) != RADIOLIB_ERR_NONE) return false;
  return join();
}

bool LoRaWANTransport::join() {
  joined_ = (node.activateOTAA() == RADIOLIB_LORAWAN_NEW_SESSION);
  return joined_;
}

bool LoRaWANTransport::send(const uint8_t* data, size_t len) {
  if (!joined_ && !join()) return false;          // still no network: this window is lost

  LoRaWANEvent_t down;
  dlLen = 0;
  const int16_t state = node.sendReceive(data, len, UPLINK_PORT, dlBuf, &dlLen, false, nullptr, &down);
  if (state < RADIOLIB_ERR_NONE) return false;
  // state > 0: a downlink arrived (in RX1 or RX2). Keep it only if it is one of our commands.
  dlPending = (state > 0 && dlLen > 0 && dlLen <= DOWNLINK_MAX_SIZE && down.fPort == DOWNLINK_PORT);
  return true;
}

bool LoRaWANTransport::pollDownlink(uint8_t* buf, size_t& len) {
  len = 0;
  if (!dlPending) return false;
  memcpy(buf, dlBuf, dlLen);
  len = dlLen;
  dlPending = false;
  return true;
}

void LoRaWANTransport::sleep() { radio.sleep(); }

}  // namespace uwsn
