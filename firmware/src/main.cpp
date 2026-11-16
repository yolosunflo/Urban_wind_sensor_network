#include <Arduino.h>
#include <Wire.h>
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

static TemperatureSensor tempSensor;
static LoRaWANTransport radio;
static PowerManager power;

static Aggregator agg;

// RAM is kept during deep sleep (STOP2), so seq only restarts at 0 after a reset or a
// battery change. The server sees that as one "missing packets" flag: fine for the prototype.
static uint16_t seq = 0;

/**
 * @brief Applies a calibration command from the server and keeps it in flash.
 * The node has no clock: this is the ONLY way its calibration changes.
 */
static void handleDownlink(const uint8_t* buf, size_t len) {
#if ANEMOMETER_TYPE == ANEMO_PULSE
  PulseCalibParams p = calib.get();          // fields the command does not carry are kept
  if (PayloadCodec::decodeCalibration(buf, len, p)) {
    calib.set(p);
    calib.save();
    Serial.println(F("New calibration applied and saved"));
  } else {
    Serial.println(F("Unknown or invalid downlink, ignored"));
  }
#else
  (void)buf; (void)len;                      // analog anemometer: downlink calibration not implemented
#endif
}

void setup() {
  Serial.begin(115200);
  Wire.setSDA(PIN_I2C_SDA);                  // I2C2 of the LoRa-E5 mini
  Wire.setSCL(PIN_I2C_SCL);

#if ANEMOMETER_TYPE == ANEMO_PULSE
  if (!calib.load()) Serial.println(F("No saved calibration, using defaults"));
#endif
  if (!sensor.begin())     Serial.println(F("Anemometer not detected"));      // windows will carry Q_SENSOR_FAULT
  if (!tempSensor.begin()) Serial.println(F("Temperature sensor not detected")); // windows will carry Q_TEMP_FAULT
  power.begin();
  if (!radio.begin())      Serial.println(F("LoRaWAN join failed, retried at each window"));
}

void loop() {
  // millis() only counts awake time (it stops during deep sleep), which is exactly what we
  // need: the time spent awake in this window, to sleep the rest of WINDOW_MS.
  const uint32_t windowStart = millis();

  // Sampling burst: SAMPLES_PER_BURST samples, one every SAMPLE_PERIOD_MS
  agg.reset();
  sensor.powerOn();
  uint32_t nextSample = millis();
  for (uint16_t i = 0; i < SAMPLES_PER_BURST; i++) {
    RawSample raw;
    if (sensor.read(raw)) agg.add(calib.apply(raw));
    else agg.addFault();

    if (i % TEMP_SAMPLE_EVERY_N == 0) {      // temperature changes slowly: read less often
      float t;
      if (tempSensor.read(t)) agg.addTemp(calib.applyTemp(t));
      else agg.addTempFault();
    }

    // Fixed rhythm: the time spent reading is not added on top of the period
    nextSample += SAMPLE_PERIOD_MS;
    const int32_t wait = (int32_t)(nextSample - millis());
    if (wait > 0) delay(wait);
  }
  sensor.powerOff();

  // Aggregate + flag quality
  WindAggregate wind_agg = agg.compute();
  if (power.isLow()) wind_agg.flags |= Q_LOW_BATTERY;

  // Encode + send (the downlink, if any, arrives during this call)
  uint8_t buf[UPLINK_SIZE];
  UplinkFrame frame = PayloadCodec::toFrame(wind_agg, seq++, power.readBatteryV());
  size_t encoded_message = PayloadCodec::encode(frame, buf);
  if (!radio.send(buf, encoded_message)) Serial.println(F("Uplink failed, window lost"));

  // New calibration from the server?
  uint8_t dl[DOWNLINK_MAX_SIZE];
  size_t dlLen = 0;
  if (radio.pollDownlink(dl, dlLen)) handleDownlink(dl, dlLen);

  // Sleep the rest of the window
  radio.sleep();
  Serial.flush();
  const uint32_t awakeMs = millis() - windowStart;
  if (awakeMs < WINDOW_MS) power.deepSleep(WINDOW_MS - awakeMs);
}
