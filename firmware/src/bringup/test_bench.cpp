// Test 8: calibration bench / whole node without radio. All sensors at once, one CSV line
// per second, with the raw values AND the values after the current calibration.
// Use it next to the reference anemometer: copy the monitor output into a .csv file
// (or log it: pio device monitor > bench.csv), note the reference speed for each step.
//
// columns: ms, pulses, dt_ms, freq_hz, speed_ms, angle_raw, dir_deg, temp_c, battery_v
// (speed_ms and dir_deg use the calibration saved in flash, defaults if none)
#include "bringup.h"
#include "Anemometer.h"
#include "TemperatureSensor.h"
#include "Calibration.h"
#include "PowerManager.h"

using namespace uwsn;

static PulseAnemometer anemo(PIN_REED, PIN_ANEMO_POWER);
static TemperatureSensor temp;
static PulseCalibration calib;
static PowerManager power;
static uint32_t n = 0;

void setup() {
  bringupBegin("calibration bench (CSV stream)");
  i2cBegin();
  printResult(anemo.begin(), F("AS5600"));
  printResult(temp.begin(), F("TMP102"));
  power.begin();
  const bool saved = calib.load();
  LOG.print(saved ? F("Saved calibration: gain ") : F("No saved calibration, defaults: gain "));
  LOG.print(calib.get().speedGain, 4);
  LOG.print(F(" m/s per Hz, offset "));
  LOG.print(calib.get().speedOffset_ms, 3);
  LOG.println(F(" m/s"));
  anemo.powerOn();
  LOG.println(F("ms,pulses,dt_ms,freq_hz,speed_ms,angle_raw,dir_deg,temp_c,battery_v"));
}

void loop() {
  delay(SAMPLE_PERIOD_MS);
  RawSample r;
  const bool ok = anemo.read(r);
  const WindSample w = calib.apply(r);
  float t = NAN;
  if (n++ % TEMP_SAMPLE_EVERY_N == 0 && temp.read(t)) t = calib.applyTemp(t);

  LOG.print(millis()); LOG.print(',');
  LOG.print(r.pulses); LOG.print(',');
  LOG.print(r.dtMs); LOG.print(',');
  LOG.print(r.dtMs ? r.pulses * 1000.0f / r.dtMs : 0.0f, 3); LOG.print(',');
  LOG.print(w.speed_ms, 3); LOG.print(',');
  if (ok) { LOG.print(r.angleRaw); LOG.print(','); LOG.print(w.dir_deg, 1); }
  else LOG.print(F(","));                                   // AS5600 failed: empty cells
  LOG.print(',');
  if (!isnan(t)) LOG.print(t, 2);                          // temperature every 10 s only
  LOG.print(',');
  LOG.println(power.readBatteryV(), 3);
}
