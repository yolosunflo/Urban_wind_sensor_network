# Payload formats

Both sides must share the constants: `firmware/include/config.h` <-> `server/uwsn/config.py`.
Everything is big-endian (most significant byte first).

## Uplink (node -> server): version 1, 14 bytes, LoRaWAN port 1

| Byte | Field       | Type   | Scale / unit                 |
|------|-------------|--------|------------------------------|
| 0    | version     | uint8  | 1                            |
| 1-2  | seq         | uint16 | counter, wraps at 65535 (restarts at 0 after a reset) |
| 3-4  | mean speed  | uint16 | x 0.01 m/s                   |
| 5-6  | gust        | uint16 | x 0.01 m/s                   |
| 7-8  | mean dir    | uint16 | x 0.1 deg (vector average)   |
| 9    | std speed   | uint8  | x 0.05 m/s                   |
| 10-11| temperature | int16  | x 0.01 C, -32768 = n/a       |
| 12   | battery     | uint8  | 2.00 V + 0.01 V x value      |
| 13   | flags       | uint8  | bit0 range, 1 stuck, 2 spike, 3 low batt, 4 calib due, 5 sensor fault, 6 few samples, 7 temperature fault |

Bits 2 (spike) and 4 (calibration due) are never set by the node: spikes are detected by the
server, and the node has no clock, so the server decides when a calibration is due.

Why fixed-point integers: LoRaWAN payloads must stay tiny (airtime = battery),
and floats would waste 4 bytes each. 0.01 m/s resolution keeps the
below-1 m/s range (the critical one for urban ventilation) usable.

## Downlink (server -> node): LoRaWAN port 2

The node changes its calibration only when it receives one of these commands (it has no
clock and never decides by itself). LoRaWAN class A: TTN keeps the command in a queue and
sends it right after the node's next uplink, so it arrives up to one window (10 min) later.
The node applies it at once and saves it in flash, so it survives a reset or a battery change.
An unknown command or a too-short payload is ignored.

### Command 0x01: set calibration (9 bytes)

| Byte | Field              | Type   | Scale / unit                                   |
|------|--------------------|--------|------------------------------------------------|
| 0    | command            | uint8  | 0x01                                           |
| 1-2  | speed gain         | uint16 | x 0.0001 m/s per Hz (0.0001 .. 6.5535; 0 is rejected) |
| 3-4  | speed offset       | int16  | x 0.001 m/s                                    |
| 5-6  | direction offset   | int16  | x 0.1 deg, added to the AS5600 angle (server sends -180 .. 180) |
| 7-8  | temperature offset | int16  | x 0.01 C, added to the TMP102 reading          |

On the node: `speed = gain x pulse frequency (Hz) + offset`.
All four values are replaced, so the server always sends the current offsets too,
even if only the speed changes.

Example: gain 1.2345, offset 0.25 m/s, direction -12.5 deg, temperature -0.3 C
-> `01 30 39 00 FA FF 83 FF E2`

### Command 0x02: reset calibration (1 byte)

`02`: back to the firmware defaults (gain 1, all offsets 0).

### Code

- Server: `CalibrationManager.build_downlink()` / `build_reset_downlink()` (`uwsn/calibration.py`),
  sent with `send_downlink()` (`uwsn/ingestion.py`).
- Node: `PayloadCodec::decodeCalibration()`, applied in `handleDownlink()` (`main.cpp`).

There is no acknowledgement: check the change in the next measurements (or on the serial monitor).
