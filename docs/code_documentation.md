# Code documentation

What each part of the code does, and the format of the radio messages.
Details of each class and function are in the comments of the files themselves.

## 1. Glossary

| Term | Meaning |
|---|---|
| **Firmware** | the C++ program inside each sensor node |
| **Server** | the Python program that receives, checks, stores, analyses and displays the data |
| **Payload** | the bytes actually sent over the radio (14 bytes per uplink) |
| **Uplink / downlink** | message node -> server / server -> node |
| **Gateway** | receives the LoRa messages of the nodes and forwards them to internet |
| **TTN** (The Things Network) | free LoRaWAN network server between the gateway and us: removes duplicates, decrypts, gives us the messages over MQTT |
| **MQTT** | messaging protocol: we subscribe to a topic on TTN and each new message is pushed to us |
| **ADC** | converts a voltage to a number; used here to read the battery voltage |

## 2. Data flow

```
NODE (C++)                                              SERVER (Python)
reed pulses + AS5600 angle + TMP102                     TTN -> MQTT -> TTNClient -> Decoder
 -> Calibration -> Aggregator (one burst per window)        -> Validator -> Repository (SQLite)
 -> PayloadCodec (14 bytes) -> LoRaWAN  --> gateway -->     -> Analyzer -> Dashboard / CSV export

calibration downlink (9 bytes, port 2)  <-- TTN <-- send_downlink() <-- CalibrationManager
```

## 3. Firmware (`firmware/`)

| File | Role |
|---|---|
| `include/config.h` | every constant: pins, timing, thresholds, payload scaling. Nothing is hard-coded elsewhere |
| `include/types.h` | data structures and quality flags |
| `include/secrets.h` | TTN keys (copied from `secrets.example.h`, never committed) |
| `Anemometer` | reads the reed pulses and the AS5600 angle (the analog driver is kept for reference only) |
| `TemperatureSensor` | reads the TMP102, one conversion on demand to save battery |
| `Calibration` | raw values -> m/s, degrees, C; keeps the parameters in flash |
| `Aggregator` | one burst of samples -> one summary (means, gust, std, flags), with running sums so no buffer in RAM |
| `PayloadCodec` | summary -> 14 bytes; decodes the calibration downlinks |
| `Transport` | LoRaWAN with RadioLib: join, send, receive downlinks |
| `PowerManager` | battery voltage and deep sleep |
| `main.cpp` | the program loop (below) |
| `src/bringup/` | hardware test programs, one per component (see `docs/testing.md`) |
| `test/test_native/` | unit tests run on the computer |
| `tools/node_sim.cpp` | the node code with fake sensors, used by the end-to-end test |

**`main.cpp`.** `setup()` loads the calibration from flash, starts the sensors and joins the
network. Each `loop()` is one window of `WINDOW_S`:
1. take `SAMPLES_PER_BURST` samples, one every `SAMPLE_PERIOD_MS` (temperature every `TEMP_SAMPLE_EVERY_N`);
2. compute the summary and its quality flags, add low battery if needed;
3. encode and send it;
4. apply a calibration downlink if one arrived;
5. deep-sleep for the rest of the window.

The node has no clock: its calibration only changes when the server sends a downlink.

## 4. Server (`server/`)

| File | Role |
|---|---|
| `main.py` | starts the service: `TTNClient` calls `Pipeline.handle_uplink` for every message |
| `uwsn/config.py` | settings: TTN, database, payload scaling (must match `config.h`), thresholds |
| `uwsn/models.py` | data structures and quality flags (bits 0-7 from the node, 8+ from the server) |
| `uwsn/ingestion.py` | the only file that knows TTN's format: receives uplinks, sends downlinks |
| `uwsn/decoder.py` | 14 bytes -> measurement (mirror of `PayloadCodec`) |
| `uwsn/validation.py` | adds flags (spike, stuck, lost packets, temperature); never deletes data |
| `uwsn/pipeline.py` | uplink -> decode -> validate -> store |
| `uwsn/storage.py` | SQLite: `sensors`, `uplinks` (raw messages), `measurements` |
| `uwsn/analysis.py` | hourly means, wind roses, calm share, availability |
| `uwsn/calibration.py` | compares a node with a reference, builds calibration downlinks |
| `uwsn/export.py` | CSV export with readable flags |
| `uwsn/dashboard/` | Streamlit web page: `streamlit run uwsn/dashboard/app.py` |
| `scripts/register_sensors.py` | stores where each node is (for the map) |
| `scripts/seed_fake_data.py` | fills a database with fake data to try the dashboard |
| `tests/` | the tests (see `docs/testing.md`) |

## 5. Payload format

Both sides must use the same constants: `firmware/include/config.h` <-> `server/uwsn/config.py`.
Everything is big-endian (most significant byte first). Integers with a fixed scale are used
instead of floats to keep messages small (airtime = battery).

### Uplink (node -> server): version 1, 14 bytes, port 1

| Byte | Field | Type | Scale / unit |
|---|---|---|---|
| 0 | version | uint8 | 1 |
| 1-2 | seq | uint16 | counter, restarts at 0 after a reset |
| 3-4 | mean speed | uint16 | x 0.01 m/s |
| 5-6 | gust | uint16 | x 0.01 m/s |
| 7-8 | mean direction | uint16 | x 0.1 deg (vector average) |
| 9 | std speed | uint8 | x 0.05 m/s |
| 10-11 | temperature | int16 | x 0.01 C, -32768 = none |
| 12 | battery | uint8 | 2.00 V + 0.01 V x value |
| 13 | flags | uint8 | bit 0 out of range, 1 stuck, 2 spike, 3 low battery, 4 calibration due, 5 sensor fault, 6 few samples, 7 temperature fault |

Bits 2 and 4 are never set by the node: the server detects spikes and decides when a
calibration is due.

### Downlink (server -> node): port 2

TTN keeps a downlink in a queue and sends it right after the node's next uplink, so it arrives
up to one window later. The node applies it and saves it in flash. Unknown or too short
commands are ignored. There is no acknowledgement: check the next measurements.

**`0x01` set calibration (9 bytes).** On the node: `speed = gain x pulse frequency + offset`.
All four values are replaced, so always send the current offsets too.

| Byte | Field | Type | Scale / unit |
|---|---|---|---|
| 0 | command | uint8 | 0x01 |
| 1-2 | speed gain | uint16 | x 0.0001 m/s per Hz (0 rejected) |
| 3-4 | speed offset | int16 | x 0.001 m/s |
| 5-6 | direction offset | int16 | x 0.1 deg, added to the vane angle |
| 7-8 | temperature offset | int16 | x 0.01 C |

Example: gain 1.2345, offset 0.25 m/s, direction -12.5 deg, temperature -0.3 C ->
`01 30 39 00 FA FF 83 FF E2`

**`0x02` reset calibration (1 byte):** back to gain 1, all offsets 0.

**In the code:** server `CalibrationManager.build_downlink()` / `build_reset_downlink()`, sent
with `send_downlink()`; node `PayloadCodec::decodeCalibration()`, applied in `handleDownlink()`.
