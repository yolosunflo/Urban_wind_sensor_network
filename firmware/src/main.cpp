#include <Arduino.h>
#include "config.h"
#include "Anemometer.h"
#include "TemperatureSensor.h"
#include "Calibration.h"
#include "Aggregator.h"
#include "PayloadCodec.h"
#include "Transport.h"
#include "PowerManager.h"

using namespace uwsn;

// Anemometer driver and its calibration always go in pairs (see ANEMOMETER_TYPE in config.h)
#if ANEMOMETER_TYPE == ANEMO_ANALOG
static AnalogAnemometer  sensor(PIN_SPEED_ADC, PIN_DIR_ADC, PIN_SENSOR_POWER);
static AnalogCalibration calib;
#elif ANEMOMETER_TYPE == ANEMO_PULSE
static PulseAnemometer   sensor(PIN_REED, PIN_ANEMO_POWER);
static PulseCalibration  calib;
#endif

static AnalogTemperatureSensor tempSensor(PIN_TEMP_ADC);
static LoRaWANTransport radio;
static PowerManager power;

static Aggregator agg;

static uint16_t seq = 0;   // TODO: persist across resets

void setup() {
  Serial.begin(115200);
  sensor.begin();
  tempSensor.begin();
  power.begin();
  calib.load();
  radio.begin();
}

void loop() {
  // Sampling burst
  agg.reset();
  sensor.powerOn();
  const uint32_t t0 = millis();
  uint16_t sample_count = 0;                     // sample counter
  while (millis() - t0 < BURST_S * 1000UL) {
    RawSample raw;
    if (sensor.read(raw)) agg.add(calib.apply(raw));
    if (sample_count++ % TEMP_SAMPLE_EVERY_N == 0) {      // temperature changes slowly: read less often
      float t;
      if (tempSensor.read(t)) agg.addTemp(calib.applyTemp(t));
    }
    delay(SAMPLE_PERIOD_MS);
  }
  sensor.powerOff();

  // Aggregate + flag quality
  WindAggregate wind_agg = agg.compute();
  if (power.isLow()) wind_agg.flags |= Q_LOW_BATTERY;
  // TODO: needs a real clock (RTC or network time) for calib.isDue(now)

  // Encode + send
  uint8_t buf[UPLINK_SIZE];
  UplinkFrame frame = PayloadCodec::toFrame(wind_agg, seq++, power.readBatteryV());
  size_t encoded_message = PayloadCodec::encode(frame, buf);
  radio.send(buf, encoded_message); // TODO

  // 4. Handle downlink (new calibration / new interval)
  uint8_t dl[16]; size_t dlLen = 0;
  if (radio.pollDownlink(dl, dlLen)) {
    // TODO: parse command -> calib.set(...); calib.save();
  }

  // 5. Sleep the rest of the window
  radio.sleep();
  if (WINDOW_S > BURST_S) power.deepSleep((WINDOW_S - BURST_S) * 1000UL);
}