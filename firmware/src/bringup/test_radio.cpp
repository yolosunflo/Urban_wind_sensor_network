// Test 7: LoRaWAN radio, with the real LoRaWANTransport (needs include/secrets.h and the
// antenna). Joins TTN, then sends a FAKE but valid uplink every 60 s (fake sensor values,
// so it works with no sensor connected), and prints any downlink it receives.
// Check:
//   - "join OK" (can take up to a minute; the gateway must be online in the TTN console)
//   - the messages appear in the TTN console, Live data, every 60 s
//   - if the server runs (python main.py), they appear in the database / dashboard:
//     mean speed 1.23 m/s, gust 2.50 m/s, from 225 deg, 18.50 C
//   - send a downlink (send_downlink() or the TTN console, port 2): it is printed here
//     right after the next uplink
#include "bringup.h"
#include "Transport.h"
#include "PayloadCodec.h"
#include "PowerManager.h"

using namespace uwsn;

static LoRaWANTransport radio;
static PowerManager power;
static uint16_t seq = 0;

void setup() {
  bringupBegin("LoRaWAN radio");
  power.begin();
  LOG.println(F("Joining TTN..."));
  printResult(radio.begin(), F("join"));
}

void loop() {
  WindAggregate fake{};
  fake.meanSpeed_ms = 1.23f; fake.gust_ms = 2.5f; fake.meanDir_deg = 225.0f; fake.stdSpeed_ms = 0.4f;
  fake.hasTemp = true; fake.meanTemp_c = 18.5f; fake.nSamples = SAMPLES_PER_BURST; fake.flags = Q_OK;

  uint8_t buf[UPLINK_SIZE];
  const size_t n = PayloadCodec::encode(PayloadCodec::toFrame(fake, seq, power.readBatteryV()), buf);
  LOG.print(F("\nuplink seq "));
  LOG.print(seq++);
  LOG.print(F(": "));
  for (size_t i = 0; i < n; i++) { if (buf[i] < 16) LOG.print('0'); LOG.print(buf[i], HEX); }
  LOG.println();
  printResult(radio.send(buf, n), F("sent (a failure here usually means: not joined yet)"));

  uint8_t dl[DOWNLINK_MAX_SIZE];
  size_t dlLen = 0;
  if (radio.pollDownlink(dl, dlLen)) {
    LOG.print(F("DOWNLINK received ("));
    LOG.print(dlLen);
    LOG.print(F(" bytes): "));
    for (size_t i = 0; i < dlLen; i++) { if (dl[i] < 16) LOG.print('0'); LOG.print(dl[i], HEX); }
    LOG.println();
    PulseCalibParams p;
    LOG.println(PayloadCodec::decodeCalibration(dl, dlLen, p) ? F("  -> valid calibration command")
                                                             : F("  -> not a valid calibration command"));
  }
  radio.sleep();
  delay(60000);      // TTN fair use: keep tests at one message per minute or slower
}
