// Node simulator: the REAL node code (Calibration, Aggregator, PayloadCodec) fed with fake
// sensor values, on the computer. Used by server/tests/test_end_to_end.py; you can also
// play with it by hand:
//
//   g++ -std=c++17 -Iinclude -Isrc tools/node_sim.cpp src/Aggregator.cpp src/PayloadCodec.cpp \
//       src/Calibration.cpp -o node_sim
//   ./node_sim
//
// Commands (one per line on stdin):
//   window <freq_hz> <dir_deg> <temp_c | none> [fault_every]
//        one burst with a constant wind: freq_hz reed pulses per second, vane at dir_deg.
//        fault_every N: one anemometer read in N fails (0 = never).
//        prints:  uplink <28 hex characters>
//   calib <hex>      apply a downlink (as handleDownlink() in main.cpp): prints calib ok | calib rejected
//   reset            simulate a reboot: seq back to 0, calibration reloaded from "flash"
//   quit
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "config.h"
#include "types.h"
#include "Calibration.h"
#include "Aggregator.h"
#include "PayloadCodec.h"

using namespace uwsn;

static PulseCalibration calib;
static uint16_t seq = 0;

static std::string toHex(const uint8_t* b, size_t n) {
  static const char* d = "0123456789abcdef";
  std::string s;
  for (size_t i = 0; i < n; i++) { s += d[b[i] >> 4]; s += d[b[i] & 15]; }
  return s;
}

static bool fromHex(const std::string& h, std::vector<uint8_t>& out) {
  if (h.size() % 2) return false;
  for (size_t i = 0; i < h.size(); i += 2) out.push_back((uint8_t)strtoul(h.substr(i, 2).c_str(), nullptr, 16));
  return true;
}

static void window(float freqHz, float dirDeg, bool hasTemp, float tempC, unsigned faultEvery) {
  Aggregator agg;
  float pulseAcc = 0;                                   // fractional pulses carried over
  for (unsigned i = 0; i < SAMPLES_PER_BURST; i++) {
    pulseAcc += freqHz * SAMPLE_PERIOD_MS / 1000.0f;
    RawSample r{};
    r.pulses = (uint16_t)pulseAcc;
    pulseAcc -= r.pulses;
    r.dtMs = SAMPLE_PERIOD_MS;
    const float wobble = (i % 4) * 2.0f - 3.0f;         // the vane always moves a little
    r.angleRaw = (uint16_t)lroundf(fmodf(dirDeg + wobble + 360.0f, 360.0f) * 4096.0f / 360.0f) % 4096;

    if (faultEvery && i % faultEvery == 0) agg.addFault();
    else agg.add(calib.apply(r));

    if (i % TEMP_SAMPLE_EVERY_N == 0) {
      if (hasTemp) agg.addTemp(calib.applyTemp(tempC));
      else agg.addTempFault();
    }
  }
  uint8_t buf[UPLINK_SIZE];
  PayloadCodec::encode(PayloadCodec::toFrame(agg.compute(), seq++, 3.6f), buf);
  printf("uplink %s\n", toHex(buf, UPLINK_SIZE).c_str());
}

int main() {
  calib.load();
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string cmd;
    in >> cmd;
    if (cmd == "window") {
      float f, d; std::string t; unsigned every = 0;
      in >> f >> d >> t >> every;
      const bool hasTemp = (t != "none");
      window(f, d, hasTemp, hasTemp ? strtof(t.c_str(), nullptr) : 0.0f, every);
    } else if (cmd == "calib") {
      std::string h; in >> h;
      std::vector<uint8_t> b;
      PulseCalibParams p = calib.get();
      if (fromHex(h, b) && PayloadCodec::decodeCalibration(b.data(), b.size(), p)) {
        calib.set(p); calib.save();
        puts("calib ok");
      } else {
        puts("calib rejected");
      }
    } else if (cmd == "reset") {
      seq = 0;
      calib.set(PulseCalibParams{});
      calib.load();
      puts("reset ok");
    } else if (cmd == "quit") {
      break;
    } else if (!cmd.empty()) {
      printf("unknown command %s\n", cmd.c_str());
    }
    fflush(stdout);
  }
  return 0;
}
