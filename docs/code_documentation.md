# Code documentation: Urban Wind Sensor Network

This document explains what each file, class and function of the skeleton is for.
Read the glossary first, then the firmware (the sensor node), then the server.


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

## 1. Overall data flow

```
 SENSOR NODE (C++)                                   SERVER (Python)
 anemometer -> ADC -> Calibration -> Aggregator      Ingestor -> Decoder -> Validator
            -> PayloadCodec -> Transport (LoRa)  --> Repository -> Analyzer -> Dashboard / Export
                                  |                      ^
                                  v                      |
                              gateway -> TTN ---- MQTT --+
```

## 2. Firmware (C++), folder `firmware/`

**`include/config.h`**: all the tunable constants.
Not a class. It groups the settings so that nothing is hard-coded elsewhere:

**`include/types.h`**: the data structures

**`Anemometer.h / .cpp`**: talking to the sensor. Abstract class to adapt for Analog or Pulse anemometer.

**`TemperatureSensor.h / .cpp`**: air temperature.
Temperature changes slowly, so it is read only every `TEMP_SAMPLE_EVERY_N` wind samples.

**`Calibration.h / .cpp`**: raw counts to physical values.

**`Aggregator.h / .cpp`**: from 600 samples to 1 summary.
It keeps *running sums* instead of storing all the samples, which saves RAM.

**`PayloadCodec.h / .cpp`**: from numbers to bytes. Converts floats to fixed-point integers and then to 14 bytes (big-endian) message.

**`Transport.h / .cpp`**: the radio

**`PowerManager.h / .cpp`**: Handles the power consumption of the module

### `main.cpp`: the program loop
`setup()` runs once: starts the sensor, power manager, calibration, radio.
`loop()` repeats forever, one pass per sampling window:
1. Power on the sensor and sample every second (`BURST_S`), feeding each calibrated sample to the aggregator. Every 10th sample the temperature is also read, corrected and added to the aggregator.
2. Power off the sensor, compute the aggregate, read the battery, add a low-battery flag if needed.
3. Build the payload and send it.
4. Check for a downlink (new calibration).
5. Sleep until the next window.


## 3. Server (Python), folder `server/`

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
  - `validate(Measurement)`: adds flags for: physically impossible values, a sudden jump versus the previous window (spike), identical values repeated many times (stuck), a gap in sequence numbers (lost packets), a missing, impossible or suddenly jumping temperature (this only flags the temperature, the wind data stays usable), and low battery. It never deletes anything.

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
  - `hourly()`: mean speed, max gust and mean temperature per sensor per hour.
  - `wind_rose()`: how often wind comes from each direction, per speed class (TODO).
  - `low_wind_fraction(threshold)`: proportion of time with wind below e.g. 1 m/s per sensor, a key indicator of poor ventilation.
  - `wind_temperature_correlation()`: correlation between wind speed and the node's own temperature, per sensor. A negative value suggests that wind brings cooler air.
  - `compare_with_temperature()`: compare with an external temperature dataset, e.g. the city's existing network (TODO).
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
