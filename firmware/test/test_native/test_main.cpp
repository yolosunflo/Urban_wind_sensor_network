// Unit tests of the node logic, run on the computer (no board needed):
//     cd firmware
//     pio test -e native
// They cover Calibration, Aggregator and PayloadCodec: everything between the raw sensor
// values and the bytes sent over the radio.
#include <unity.h>
#include <math.h>
#include <string.h>
#include "config.h"
#include "types.h"
#include "Calibration.h"
#include "Aggregator.h"
#include "PayloadCodec.h"

using namespace uwsn;

void setUp() {}
void tearDown() {}

// ---------------------------------------------------------------- helpers

static RawSample raw(uint16_t pulses, uint16_t dtMs, float dirDeg) {
  RawSample r{};
  r.pulses = pulses;
  r.dtMs = dtMs;
  r.angleRaw = (uint16_t)lroundf(dirDeg * 4096.0f / 360.0f) % 4096;
  return r;
}

static WindSample wind(float speed, float dir) { return WindSample{speed, dir, 0}; }

// Fills a whole burst with the same sample
static void fillBurst(Aggregator& a, float speed, float dir) {
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) a.add(wind(speed, dir));
}

// ---------------------------------------------------------------- Calibration

void test_pulses_to_speed_uses_gain_and_offset() {
  PulseCalibration c;
  PulseCalibParams p;
  p.speedGain = 0.8f;
  p.speedOffset_ms = 0.3f;
  c.set(p);
  // 5 pulses in 1 s = 5 Hz -> 0.8 * 5 + 0.3 = 4.3 m/s
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 4.3f, c.apply(raw(5, 1000, 0)).speed_ms);
  // same frequency over 2 s
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 4.3f, c.apply(raw(10, 2000, 0)).speed_ms);
}

void test_no_pulse_is_zero_speed_not_the_offset() {
  PulseCalibration c;
  PulseCalibParams p;
  p.speedOffset_ms = 0.3f;
  c.set(p);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, c.apply(raw(0, 1000, 0)).speed_ms);
}

void test_direction_offset_wraps_around_north() {
  PulseCalibration c;
  PulseCalibParams p;
  p.dirOffsetDeg = 20.0f;
  c.set(p);
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 10.0f, c.apply(raw(0, 1000, 350.0f)).dir_deg);   // 350 + 20 = 370 -> 10
  p.dirOffsetDeg = -20.0f;
  c.set(p);
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 350.0f, c.apply(raw(0, 1000, 10.0f)).dir_deg);   // 10 - 20 = -10 -> 350
}

void test_temperature_offset() {
  PulseCalibration c;
  PulseCalibParams p;
  p.tempOffsetC = -0.4f;
  c.set(p);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 20.6f, c.applyTemp(21.0f));
}

void test_save_then_load_gives_back_the_same_values() {
  PulseCalibration c;
  PulseCalibParams p;
  p.speedGain = 1.5f;
  c.set(p);
  c.save();
  PulseCalibration other;
  TEST_ASSERT_TRUE(other.load());
  TEST_ASSERT_EQUAL_FLOAT(1.5f, other.get().speedGain);
}

// ---------------------------------------------------------------- Downlink decoding

void test_set_calibration_command() {
  // same bytes as the example in docs/payload_format.md
  const uint8_t dl[] = {0x01, 0x30, 0x39, 0x00, 0xFA, 0xFF, 0x83, 0xFF, 0xE2};
  PulseCalibParams p;
  TEST_ASSERT_TRUE(PayloadCodec::decodeCalibration(dl, sizeof dl, p));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.2345f, p.speedGain);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.25f, p.speedOffset_ms);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, -12.5f, p.dirOffsetDeg);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, -0.3f, p.tempOffsetC);
  TEST_ASSERT_EQUAL_UINT16(4096, p.angleCountsPerTurn);        // not in the command: kept
}

void test_reset_command() {
  PulseCalibParams p;
  p.speedGain = 3.0f;
  const uint8_t dl[] = {0x02};
  TEST_ASSERT_TRUE(PayloadCodec::decodeCalibration(dl, sizeof dl, p));
  TEST_ASSERT_EQUAL_FLOAT(1.0f, p.speedGain);
}

void test_bad_commands_change_nothing() {
  PulseCalibParams p;
  p.speedGain = 2.0f;
  const uint8_t tooShort[] = {0x01, 0x30, 0x39};
  const uint8_t unknown[]  = {0x7F, 0, 0, 0, 0, 0, 0, 0, 0};
  const uint8_t zeroGain[] = {0x01, 0x00, 0x00, 0, 0, 0, 0, 0, 0};
  TEST_ASSERT_FALSE(PayloadCodec::decodeCalibration(tooShort, sizeof tooShort, p));
  TEST_ASSERT_FALSE(PayloadCodec::decodeCalibration(unknown, sizeof unknown, p));
  TEST_ASSERT_FALSE(PayloadCodec::decodeCalibration(zeroGain, sizeof zeroGain, p));
  TEST_ASSERT_FALSE(PayloadCodec::decodeCalibration(tooShort, 0, p));
  TEST_ASSERT_EQUAL_FLOAT(2.0f, p.speedGain);
}

// ---------------------------------------------------------------- Aggregator

void test_mean_gust_and_std() {
  Aggregator a;
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) a.add(wind(i % 2 ? 3.0f : 1.0f, 90.0f));
  WindAggregate w = a.compute();
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 2.0f, w.meanSpeed_ms);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 3.0f, w.gust_ms);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.0f, w.stdSpeed_ms);
  TEST_ASSERT_EQUAL_UINT16(SAMPLES_PER_BURST, w.nSamples);
}

void test_mean_direction_around_north_is_not_180() {
  Aggregator a;
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) a.add(wind(2.0f, i % 2 ? 350.0f : 10.0f));
  const float d = a.compute().meanDir_deg;
  TEST_ASSERT_TRUE(d < 0.5f || d > 359.5f);
}

void test_good_window_has_no_flag() {
  Aggregator a;
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) a.add(wind(2.0f, 90.0f + (i % 5)));   // vane moves a bit
  a.addTemp(20.0f);
  TEST_ASSERT_EQUAL_UINT8(Q_OK, a.compute().flags);
}

void test_few_samples_flag() {
  Aggregator a;
  for (unsigned i = 0; i < SAMPLES_PER_BURST / 2; i++) a.add(wind(2.0f, 90.0f + (i % 5)));
  a.addTemp(20.0f);
  TEST_ASSERT_TRUE(a.compute().flags & Q_FEW_SAMPLES);
}

void test_sensor_fault_flag_only_when_most_reads_fail() {
  Aggregator a;                                   // 1 read in 10 fails: no fault
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) {
    if (i % 10 == 0) a.addFault(); else a.add(wind(2.0f, 90.0f + (i % 5)));
  }
  TEST_ASSERT_FALSE(a.compute().flags & Q_SENSOR_FAULT);

  a.reset();                                      // 2 reads in 3 fail: fault
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) {
    if (i % 3 == 0) a.add(wind(2.0f, 90.0f)); else a.addFault();
  }
  TEST_ASSERT_TRUE(a.compute().flags & Q_SENSOR_FAULT);

  a.reset();                                      // sensor never answers
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) a.addFault();
  TEST_ASSERT_TRUE(a.compute().flags & Q_SENSOR_FAULT);
}

void test_out_of_range_flag() {
  Aggregator a;
  fillBurst(a, 2.0f, 90.0f);
  a.add(wind(SPEED_MAX_MS + 1.0f, 90.0f));
  TEST_ASSERT_TRUE(a.compute().flags & Q_OUT_OF_RANGE);
}

void test_stuck_vane_flag() {
  Aggregator a;
  fillBurst(a, STUCK_MIN_SPEED_MS + 2.0f, 123.0f);   // windy, vane never moves
  TEST_ASSERT_TRUE(a.compute().flags & Q_STUCK);
}

void test_calm_and_still_is_not_stuck() {
  Aggregator a;
  fillBurst(a, 0.0f, 123.0f);                         // no wind, vane still: normal
  a.addTemp(5.0f);
  TEST_ASSERT_FALSE(a.compute().flags & Q_STUCK);
}

void test_temperature_mean_and_fault() {
  Aggregator a;
  fillBurst(a, 2.0f, 90.0f);
  a.addTemp(20.0f);
  a.addTemp(22.0f);
  WindAggregate w = a.compute();
  TEST_ASSERT_TRUE(w.hasTemp);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 21.0f, w.meanTemp_c);
  TEST_ASSERT_FALSE(w.flags & Q_TEMP_FAULT);

  a.reset();
  fillBurst(a, 2.0f, 90.0f);
  a.addTempFault();                                   // no good temperature at all
  w = a.compute();
  TEST_ASSERT_FALSE(w.hasTemp);
  TEST_ASSERT_TRUE(w.flags & Q_TEMP_FAULT);
}

// ---------------------------------------------------------------- PayloadCodec

void test_encode_decode_roundtrip() {
  WindAggregate w{};
  w.meanSpeed_ms = 3.21f; w.gust_ms = 7.5f; w.meanDir_deg = 271.3f; w.stdSpeed_ms = 0.8f;
  w.hasTemp = true; w.meanTemp_c = -4.56f; w.flags = Q_LOW_BATTERY;
  UplinkFrame f = PayloadCodec::toFrame(w, 1234, 3.65f);
  uint8_t buf[UPLINK_SIZE];
  TEST_ASSERT_EQUAL(UPLINK_SIZE, PayloadCodec::encode(f, buf));
  UplinkFrame g{};
  TEST_ASSERT_TRUE(PayloadCodec::decode(buf, sizeof buf, g));
  TEST_ASSERT_EQUAL_UINT16(1234, g.seq);
  TEST_ASSERT_EQUAL_UINT16(321, g.meanSpeed);
  TEST_ASSERT_EQUAL_UINT16(750, g.gust);
  TEST_ASSERT_EQUAL_UINT16(2713, g.meanDir);
  TEST_ASSERT_EQUAL_UINT8(16, g.stdSpeed);
  TEST_ASSERT_EQUAL_INT16(-456, g.temp);
  TEST_ASSERT_EQUAL_UINT8(165, g.battery);
  TEST_ASSERT_EQUAL_UINT8(Q_LOW_BATTERY, g.flags);
}

void test_known_bytes_big_endian() {
  WindAggregate w{};
  w.meanSpeed_ms = 1.5f; w.gust_ms = 3.2f; w.meanDir_deg = 270.0f; w.stdSpeed_ms = 0.5f;
  w.hasTemp = false;
  uint8_t buf[UPLINK_SIZE];
  PayloadCodec::encode(PayloadCodec::toFrame(w, 42, 3.9f), buf);
  // same bytes as the server test test_decoder.py::test_roundtrip_known_payload
  const uint8_t expected[UPLINK_SIZE] = {1, 0, 42, 0, 150, 1, 64, 10, 140, 10, 0x80, 0x00, 190, 0};
  TEST_ASSERT_EQUAL_HEX8_ARRAY(expected, buf, UPLINK_SIZE);
}

void test_values_are_clamped_and_direction_wraps() {
  WindAggregate w{};
  w.meanSpeed_ms = 1000.0f;          // more than uint16 can hold
  w.stdSpeed_ms = -1.0f;             // negative
  w.meanDir_deg = 359.99f;           // rounds to 360.0 -> must be sent as 0
  UplinkFrame f = PayloadCodec::toFrame(w, 0, 10.0f);
  TEST_ASSERT_EQUAL_UINT16(65535, f.meanSpeed);
  TEST_ASSERT_EQUAL_UINT8(0, f.stdSpeed);
  TEST_ASSERT_EQUAL_UINT16(0, f.meanDir);
  TEST_ASSERT_EQUAL_UINT8(255, f.battery);
  TEST_ASSERT_EQUAL_INT16(INT16_MIN, f.temp);   // no temperature
}

void test_decode_refuses_short_buffer() {
  uint8_t buf[UPLINK_SIZE] = {0};
  UplinkFrame f{};
  TEST_ASSERT_FALSE(PayloadCodec::decode(buf, UPLINK_SIZE - 1, f));
}

// ---------------------------------------------------------------- big test: one whole window

void test_whole_window_raw_samples_to_bytes() {
  // Raw readings as the sensors would give them -> calibration -> aggregation -> bytes
  PulseCalibration c;
  PulseCalibParams p;
  p.speedGain = 0.5f;               // 4 Hz -> 2.0 m/s
  c.set(p);
  Aggregator a;
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) {
    a.add(c.apply(raw(4, SAMPLE_PERIOD_MS, 45.0f + (i % 3))));
    if (i % TEMP_SAMPLE_EVERY_N == 0) a.addTemp(c.applyTemp(12.0f));
  }
  uint8_t buf[UPLINK_SIZE];
  PayloadCodec::encode(PayloadCodec::toFrame(a.compute(), 7, 3.6f), buf);
  UplinkFrame f{};
  PayloadCodec::decode(buf, sizeof buf, f);
  TEST_ASSERT_EQUAL_UINT16(200, f.meanSpeed);               // 2.00 m/s
  TEST_ASSERT_UINT16_WITHIN(15, 460, f.meanDir);            // ~46 deg
  TEST_ASSERT_EQUAL_INT16(1200, f.temp);                    // 12.00 C
  TEST_ASSERT_EQUAL_UINT8(Q_OK, f.flags);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_pulses_to_speed_uses_gain_and_offset);
  RUN_TEST(test_no_pulse_is_zero_speed_not_the_offset);
  RUN_TEST(test_direction_offset_wraps_around_north);
  RUN_TEST(test_temperature_offset);
  RUN_TEST(test_save_then_load_gives_back_the_same_values);
  RUN_TEST(test_set_calibration_command);
  RUN_TEST(test_reset_command);
  RUN_TEST(test_bad_commands_change_nothing);
  RUN_TEST(test_mean_gust_and_std);
  RUN_TEST(test_mean_direction_around_north_is_not_180);
  RUN_TEST(test_good_window_has_no_flag);
  RUN_TEST(test_few_samples_flag);
  RUN_TEST(test_sensor_fault_flag_only_when_most_reads_fail);
  RUN_TEST(test_out_of_range_flag);
  RUN_TEST(test_stuck_vane_flag);
  RUN_TEST(test_calm_and_still_is_not_stuck);
  RUN_TEST(test_temperature_mean_and_fault);
  RUN_TEST(test_encode_decode_roundtrip);
  RUN_TEST(test_known_bytes_big_endian);
  RUN_TEST(test_values_are_clamped_and_direction_wraps);
  RUN_TEST(test_decode_refuses_short_buffer);
  RUN_TEST(test_whole_window_raw_samples_to_bytes);
  return UNITY_END();
}
