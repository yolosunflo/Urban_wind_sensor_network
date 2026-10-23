#include <Arduino.h>
#include "config.h"
#include "Anemometer.h"
#include "Calibration.h"
#include "Aggregator.h"
#include "PayloadCodec.h"
#include "Transport.h"
#include "PowerManager.h"

using namespace uwsn;

static AnalogAnemometer sensor(PIN_SPEED_ADC, PIN_DIR_ADC, PIN_SENSOR_POWER);
static Calibration      calib;
static Aggregator       agg;
static LoRaWANTransport radio;
static PowerManager     power;
static uint16_t         seq = 0;   // TODO: persist across resets

void setup() {
  Serial.begin(115200);
  sensor.begin();
  power.begin();
  calib.load();
  radio.begin();
}

void loop() {
  // 1. Sampling burst
  agg.reset();
  sensor.powerOn();
  const uint32_t t0 = millis();
  while (millis() - t0 < BURST_S * 1000UL) {
    RawSample raw;
    if (sensor.read(raw)) agg.add(calib.apply(raw));
    delay(SAMPLE_PERIOD_MS);          // TODO: light sleep instead of delay
  }
  sensor.powerOff();

  // 2. Aggregate + flag quality
  WindAggregate a = agg.compute();
  const float vbat = power.readBatteryV();
  if (vbat < LOW_BATTERY_V) a.flags |= Q_LOW_BATTERY;
  // TODO: needs a real clock (RTC or network time) for calib.isDue(now)

  // 3. Encode + send
  uint8_t buf[UPLINK_SIZE];
  UplinkFrame f = PayloadCodec::toFrame(a, seq++, vbat, false, 0.0f);
  size_t n = PayloadCodec::encode(f, buf, sizeof(buf));
  if (n) radio.send(buf, n);

  // 4. Handle downlink (new calibration / new interval)
  uint8_t dl[16]; size_t dlLen = 0;
  if (radio.pollDownlink(dl, dlLen)) {
    // TODO: parse command -> calib.set(...); calib.save();
  }

  // 5. Sleep the rest of the window
  radio.sleep();
  if (WINDOW_S > BURST_S) power.deepSleep((WINDOW_S - BURST_S) * 1000UL);
}
