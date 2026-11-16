// Test 5: reed switch (cups), with the real PulseAnemometer driver and its debounce.
// Prints once per second: pulses in that second, frequency, and the total since the start.
// Check:
//   - turn the cups slowly by exactly ONE turn: the total must go up by the number of
//     magnets (1 pulse per magnet pass, never 2 = bounce, never 0 = magnet too far)
//   - spin them fast (fan, drill at low speed): the frequency must follow smoothly
// Type 'r' + Enter in the monitor to reset the total.
#include "bringup.h"
#include "Anemometer.h"

using namespace uwsn;

static PulseAnemometer anemo(PIN_REED, PIN_ANEMO_POWER);
static uint32_t total = 0;

void setup() {
  bringupBegin("reed switch (cups)");
  i2cBegin();
  if (!anemo.begin()) LOG.println(F("(AS5600 not answering: fine for this test, only the reed is tested)"));
  anemo.powerOn();                      // pull-up on, interrupt attached, counter at 0
  LOG.print(F("Reed on pin PB4, debounce "));
  LOG.print(REED_DEBOUNCE_US);
  LOG.println(F(" us. Turn the cups..."));
  LOG.println(F("\n pulses/s   freq (Hz)   total   pin now"));
}

void loop() {
  delay(1000);
  if (LOG.available() && LOG.read() == 'r') { total = 0; LOG.println(F("total reset")); }
  RawSample r;
  anemo.read(r);                        // returns false without AS5600, the pulses are still counted
  total += r.pulses;
  LOG.print(F("   "));
  LOG.print(r.pulses);
  LOG.print(F("          "));
  LOG.print(r.dtMs ? r.pulses * 1000.0f / r.dtMs : 0.0f, 2);
  LOG.print(F("       "));
  LOG.print(total);
  LOG.print(F("     "));
  LOG.println(digitalRead(PIN_REED) ? F("open") : F("CLOSED (magnet on the switch)"));
}
