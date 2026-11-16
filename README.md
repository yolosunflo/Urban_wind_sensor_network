# Urban Wind Sensor Network

Battery-powered nodes on street lamps measure wind speed, wind direction and air temperature,
send a summary over LoRaWAN, and a Python server checks, stores, analyses and
displays the data.

## Hardware (prototype)

| Part | What we use |
|---|---|
| Microcontroller + radio | Seeed LoRa-E5 mini (STM32WLE5JC, LoRaWAN built in) |
| Wind speed | Our own 3-cup anemometer: magnet + reed switch, one pulse per pass |
| Wind direction | AS5600 magnetic angle sensor (I2C) on the vane |
| Temperature | SparkFun SEN-13314 (TI TMP102, I2C) |
| Power | 3.6 V Li-SOCl2 battery + TPS61023 boost to 5 V; battery read through a voltage divider |
| Network | LoRaWAN gateway -> The Things Network (TTN) -> MQTT -> our server |

The code also has a driver for an anemometer with analog outputs (`ANEMO_ANALOG`). It is kept
for reference only; the node uses `ANEMO_PULSE` (see `firmware/include/config.h`).

## Folders

- `firmware/`: C++ (PlatformIO, Arduino framework) running on each node
- `server/`: Python (ingestion, validation, storage, analysis, calibration, dashboard)
- `docs/payload_format.md`: the uplink and downlink formats, the contract between the two
- `docs/code_documentation.md`: what each file, class and function does
- `REQ.md`: requirements

## Data flow

```
NODE                                                    SERVER
reed pulses + AS5600 angle + TMP102                     TTN -> MQTT -> TTNClient -> Decoder
 -> Calibration -> Aggregator (one burst per window)        -> Validator -> Repository (SQLite)
 -> PayloadCodec (14 bytes) -> LoRaWAN  --> gateway -->     -> Analyzer -> Dashboard / CSV export

calibration downlink (9 bytes, port 2)  <-- TTN <-- send_downlink() <-- CalibrationManager
```

## Timing

Every `WINDOW_S` the node samples for `BURST_S` at one sample per
`SAMPLE_PERIOD_MS`, sends one summary, then deep-sleeps for the rest of the window.
Change these numbers only in `firmware/include/config.h`; everything else is derived from them.
`window_s` in `server/uwsn/config.py` must stay equal to `WINDOW_S`.

## Calibration

The node has no clock and never decides by itself that it needs calibrating. The server
compares a node with a reference (`CalibrationManager.check_drift()`), computes new values
and sends them in a downlink. The node applies them at once and keeps them in flash.
See `docs/payload_format.md` for the format.

## Server: quick start

```
cd server
pip install -r requirements.txt
python scripts/seed_fake_data.py         # fake data, to try without hardware
streamlit run uwsn/dashboard/app.py      # dashboard in the browser
python -m pytest                         # tests
```

To receive real data, set `TTN_APP_ID` and `TTN_API_KEY` (environment variables, never in git),
then run `python main.py`. The API key needs read rights on uplinks and, for calibration,
write rights on downlinks.

## Firmware: quick start

1. Install PlatformIO (VS Code extension).
2. Copy `firmware/include/secrets.example.h` to `secrets.h` and fill in the keys from the TTN
   console. `secrets.h` must never be committed.
3. Connect an ST-Link to the SWD pins of the LoRa-E5 mini (the board has no debug probe).
   The first time, remove the read protection of the factory AT firmware with STM32CubeProgrammer.
4. `pio run -t upload`, then `pio device monitor` (USB-C) to see the log.

Wiring (LoRa-E5 mini): I2C SDA PA15 / SCL PB15 (AS5600 + TMP102), reed switch PB4 to GND,
battery divider on PB3. Pins are set in `firmware/include/config.h`.
