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

**`uwsn/config.py`**: settings. TTN connection info, database path, payload scaling, validation thresholds.

**`uwsn/models.py`**: the data structures

**`uwsn/ingestion.py`**: receiving the data (the "entry door"). Our nodes send over LoRaWAN to our gateway, which forwards to TTN; TTN publishes each uplink as JSON on its MQTT broker.
This is the only file that knows TTN's message format.

**`uwsn/decoder.py`**: bytes to numbers. Mirror of `firmware/src/PayloadCodec.cpp`

**`uwsn/validation.py`**: quality control. Adds flags if an incoherent data is detected. Remembers the recent history per sensor.

**`uwsn/calibration.py`**: drift detection, compares with a reference. Build a command to send new calibration values to a node

**`uwsn/storage.py`**: the database. SQLite: three tables (`sensors`, `uplinks`, `measurements`).

**`uwsn/pipeline.py`**: the chain of action from receiving to storing.

**`uwsn/analysis.py`**: turning data into insights

**`uwsn/export.py`**: output, save a table as CSV.

### `uwsn/dashboard/app.py`: the visual interface
A Streamlit web page (run with `streamlit run uwsn/dashboard/app.py`).

### `main.py`: starting the server
Creates a `Pipeline` and tells the `TTNMqttIngestor` to call `pipeline.handle_uplink` for each message.

### `tests/test_decoder.py`
A unit test: builds a known 14-byte payload and checks that the decoder returns the expected speed, temperature and battery. Run with `pytest`.
