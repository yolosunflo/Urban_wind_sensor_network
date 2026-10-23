# Code documentation: Urban Wind Sensor Network

This document explains what each file, class and function of the skeleton is for.
Read the glossary first, then the firmware (the sensor node), then the server.

---

## 0. Glossary

| Term | Meaning |
|---|---|
| **ADC** (Analog-to-Digital Converter) | A component of the microcontroller that turns a voltage (analog, continuous) into an integer (digital). With a 12-bit ADC and a 3.3 V reference, 0 V gives 0 and 3.3 V gives 4095. The anemometer outputs a voltage, so the ADC is how the microcontroller "reads" it. |
| **Firmware** | The program running inside the microcontroller of each sensor node (our C++ code). |
| **Backend / server** | The program running on a computer or cloud server that receives, checks, stores and analyses the data (our Python code). |
| **Payload** | The small block of bytes actually sent over the radio. Ours is 14 bytes. |
| **Gateway** | The radio receiver that picks up LoRa messages from the nodes and forwards them to the internet. |
| **TTN** (The Things Network) | A free, community-run LoRaWAN *network server*. It receives the messages from gateways, checks and decrypts them, and makes them available to us (here through MQTT). It is the "post office" between the gateway and our server. |
| **MQTT** | A lightweight messaging protocol. We "subscribe" to a topic on TTN and every new sensor message is pushed to our program. |
| **Ingestion** | The step of *bringing data into our system*: receiving the raw messages that arrive from the outside (here from TTN) and handing them to the rest of our program. It is the entry door of the backend. |
| **Ingestor** | The class that performs the ingestion. It connects to TTN, listens for messages and passes each one on. |
| **Aggregator** | A piece of code that condenses many measurements into a few summary numbers. We measure once per second, which gives 600 values in 10 minutes. The aggregator reduces them to a mean speed, a gust, a mean direction and a standard deviation, so we only transmit 14 bytes. |
| **Dashboard** | A web page showing the data visually (maps, charts, tables, indicators) so that non-programmers (municipalities, researchers) can explore it. |
| **Calibration** | The conversion factors that turn a raw voltage into a correct wind speed. They can drift over time, so they must be checked and updated. |
| **Fixed-point** | Storing a decimal number as an integer by agreeing on a scale. Example: 1.53 m/s is sent as 153 with a resolution of 0.01 m/s. Smaller than a float. |
| **Vector average (direction)** | Wind direction is an angle: the mean of 359 degrees and 1 degree is 0 degrees, not 180. So we average the sin/cos components and convert back. |
| **Gust** | A short peak of wind speed (officially the maximum 3-second mean in a window). |
| **Quality flag** | A tag added to a measurement saying it may be wrong (spike, stuck sensor...). We never delete data, we flag it. |

---

## 1. Firmware (C++), folder `firmware/`

### `include/config.h`: all the tunable constants
Not a class. It groups the settings so that nothing is hard-coded elsewhere:
- **Pins**: which board pin is connected to what (speed signal, direction signal, sensor power switch, battery measurement).
- **ADC**: resolution (12 bits), reference voltage (3.3 V).
- **Sampling**: `SAMPLE_PERIOD_MS` (1 s between samples), `WINDOW_S` (one message every 600 s), `BURST_S` (how long we actually sample inside a window; shorter means more sleep and less battery use).
- **Limits**: maximum plausible speed, low-battery threshold.
- **Payload scaling**: the resolution of each field (must match the server's `config.py`).

### `include/types.h`: the data structures
- **`QualityFlag`**: a list of bits describing problems (out of range, stuck, spike, low battery, calibration due, sensor fault, too few samples). Several can be combined in one byte.
- **`RawSample`**: one reading straight from the ADC (`speedAdc`, `dirAdc`, timestamp). Integers, no physical meaning yet.
- **`WindSample`**: the same reading converted to physical units (`speed_ms`, `dir_deg`).
- **`WindAggregate`**: the summary of one 10-minute window (mean speed, gust, mean direction, std dev, number of samples, flags).
- **`UplinkFrame`**: the same summary in fixed-point integers, ready to be turned into bytes.

### `Anemometer.h / .cpp`: talking to the sensor
- **`IAnemometer`** (interface): the contract any anemometer driver must follow. This lets us change the sensor model without touching the rest of the code.
  - `begin()`: initialise the pins.
  - `read(RawSample&)`: take one reading; returns `false` if the sensor seems broken.
  - `powerOn()` / `powerOff()`: switch the sensor on (with a warm-up delay) or off to save battery.
- **`AnalogAnemometer`**: implementation for a sensor with analog voltage outputs. Attributes: `speedPin_`, `dirPin_`, `powerPin_`. Methods are the ones above; `read()` calls `analogRead()` on both channels.

### `Calibration.h / .cpp`: raw counts to physical values
- **`CalibrationParams`**: the numbers describing one node's calibration:
  - `speedOffsetV`: voltage output at 0 m/s.
  - `speedGain`: how many m/s per volt.
  - `dirOffsetDeg`: correction for how the vane was mounted.
  - `calibratedAt`: date of the last calibration.
  - `validForDays`: after this, the node reports "calibration due".
- **`Calibration`** (class):
  - `load()` / `save()`: read/write the parameters in non-volatile memory so they survive a power cut (TODO).
  - `set(params)`: replace the parameters (used when the server sends a new calibration).
  - `apply(RawSample)`: converts ADC counts to volts, then to m/s and degrees. Returns a `WindSample`.
  - `isDue(now)`: true if the calibration is too old.

### `Aggregator.h / .cpp`: from 600 samples to 1 summary
- **`Aggregator`** (class). It keeps *running sums* instead of storing all the samples, which saves RAM.
  - Attributes: `n_` (sample count), `mean_` and `m2_` (running mean and variance, "Welford" method), `maxSpeed_` (for the gust), `sumSin_` / `sumCos_` (for the vector average of direction), `sameCount_` / `maxSame_` (to detect a stuck sensor).
  - `reset()`: start a new window.
  - `add(WindSample)`: include one more sample in the running statistics.
  - `count()`: how many samples so far.
  - `compute()`: produce the `WindAggregate` and set quality flags (too few samples, out of range, stuck).

### `PayloadCodec.h / .cpp`: from numbers to bytes
- **`PayloadCodec`** (class, only static functions):
  - `toFrame(aggregate, seq, batteryV, hasTemp, tempC)`: converts the floats to fixed-point integers (with clamping so nothing overflows) and fills an `UplinkFrame`. `seq` is a message counter used by the server to detect lost packets.
  - `encode(frame, buffer, capacity)`: writes the 14 bytes (big-endian). Returns the number of bytes, or 0 on error.
  - `decode(buffer, length, frame)`: the reverse operation, useful for unit tests.

### `Transport.h / .cpp`: the radio
- **`ITransport`** (interface): the contract for any communication method, so we can swap LoRaWAN for LTE-M or mesh.
  - `begin()`: join the network.
  - `send(data, length)`: transmit one message.
  - `pollDownlink(buffer, length)`: check whether the server sent us something (new calibration, new interval).
  - `sleep()`: put the radio to sleep.
- **`LoRaWANTransport`**: the LoRaWAN implementation (currently empty `TODO`s, to be done with the RadioLib library once the module is chosen).

### `PowerManager.h / .cpp`: battery
- **`PowerManager`**:
  - `begin()`: configure the battery pin.
  - `readBatteryV()`: measure the battery voltage (through a voltage divider and the ADC).
  - `isLow()`: true below `LOW_BATTERY_V`.
  - `deepSleep(ms)`: put the microcontroller to sleep for a given time (board specific, TODO).

### `main.cpp`: the program loop
`setup()` runs once: starts the sensor, power manager, calibration, radio.
`loop()` repeats forever, one pass per 10-minute window:
1. Power on the sensor and sample every second (`BURST_S`), feeding each calibrated sample to the aggregator.
2. Power off the sensor, compute the aggregate, read the battery, add a low-battery flag if needed.
3. Build the payload and send it.
4. Check for a downlink (new calibration).
5. Sleep until the next window.

---

## 2. Server (Python), folder `server/`

### `uwsn/config.py`: settings
- **`Settings`** (dataclass): TTN connection info (read from environment variables so the secret key never goes into git), database path, payload scaling (must match the firmware), and validation thresholds (max speed, spike size, stuck windows, low battery, recalibration period).
- **`SETTINGS`**: the single instance used everywhere.

### `uwsn/models.py`: the data structures
- **`QualityFlag`**: same bits as the firmware, plus two server-only ones (`MISSING_BEFORE`: packets lost before this one; `DRIFT_SUSPECTED`: disagrees with a reference station).
- **`SensorMeta`**: description of one physical sensor (id, latitude, longitude, installation height, site description, installation date). Needed to put sensors on a map.
- **`Uplink`**: a raw message as received (device id, reception time, bytes, signal strength RSSI and SNR).
- **`Measurement`**: one decoded 10-minute window in physical units. Property `is_usable` is true if no serious flag is set.

### `uwsn/ingestion.py`: receiving the data (the "entry door")
- **`Ingestor`** (abstract class): contract with `start(callback)` and `stop()`. The callback is the function called for every new message.
- **`TTNMqttIngestor`**: connects to TTN over MQTT, subscribes to the uplinks of our application, extracts the bytes and metadata from the JSON, and calls the callback with an `Uplink`.
  - `start()`: connect and listen forever.
  - `stop()`: disconnect.
  - `_on_connect()`: subscribe to the topic once connected.
  - `_on_message()`: runs for each incoming message; decodes the base64 payload.
  This is the only file that knows TTN exists. If we change network, only this class is replaced.

### `uwsn/decoder.py`: bytes to numbers
- **`PayloadDecoder`**:
  - `decode(Uplink)`: unpacks the 14 bytes, checks the length and payload version, and applies the scaling to produce a `Measurement`. Raises an error if the message is malformed.

### `uwsn/validation.py`: quality control
- **`DataValidator`**: remembers the recent history per sensor.
  - `validate(Measurement)`: adds flags for: physically impossible values, a sudden jump versus the previous window (spike), identical values repeated many times (stuck), a gap in sequence numbers (lost packets), and low battery. It never deletes anything.

### `uwsn/calibration.py`: drift detection
- **`DriftReport`**: result of a check (gain ratio, offset, R², recalibration needed).
- **`CalibrationManager`**:
  - `check_drift(device, node_series, reference_series)`: fits a line "node vs reference". A perfect sensor has slope 1 and intercept 0; large deviations mean recalibration is needed.
  - `build_downlink(...)`: will build a command to send new calibration values to a node (TODO).

### `uwsn/storage.py`: the database
- **`Repository`** (SQLite): three tables (`sensors`, `uplinks` for raw messages, `measurements`).
  - `save_sensor()`, `save_uplink()`, `save_measurement()`: write data.
  - `load_measurements(...)`: read data as a pandas table, with optional filters (TODO).
  - `load_sensors()`: read the sensor list.

### `uwsn/pipeline.py`: gluing it together
- **`Pipeline`**:
  - `handle_uplink(Uplink)`: the function called for every message: save the raw message, decode it, validate it, save the result. A malformed message is logged and skipped instead of crashing the program.

### `uwsn/analysis.py`: turning data into insights
- **`Analyzer`** (takes a table of measurements):
  - `usable()`: keeps only measurements without serious flags.
  - `hourly()`: mean speed and max gust per sensor per hour.
  - `wind_rose()`: how often wind comes from each direction, per speed class (TODO).
  - `low_wind_fraction(threshold)`: proportion of time with wind below e.g. 1 m/s per sensor, a key indicator of poor ventilation.
  - `compare_with_temperature()`: link wind and temperature data per street (TODO).
  - `availability()`: received windows divided by expected windows, to monitor network health (TODO).

### `uwsn/export.py`: output
- **`DataExporter`**:
  - `to_csv()`: save a table as CSV.
  - `to_geojson()`: one point per sensor, for GIS/mapping tools (TODO).
  - `to_report()`: a summary report for municipalities (TODO).

### `uwsn/dashboard/app.py`: the visual interface
A Streamlit web page (run with `streamlit run uwsn/dashboard/app.py`). For now it loads the data and shows the hourly table; the `TODO` comments list what to add: filters, map with wind arrows, time series, wind rose, network health panel, CSV download.

### `main.py`: starting the server
Creates a `Pipeline` and tells the `TTNMqttIngestor` to call `pipeline.handle_uplink` for each message.

### `tests/test_decoder.py`
A unit test: builds a known 14-byte payload and checks that the decoder returns the expected speed, temperature and battery. Run with `pytest`.
