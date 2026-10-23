# Uplink payload format (version 1), 14 bytes, big-endian, LoRaWAN port 1

| Byte | Field       | Type   | Scale / unit                 |
|------|-------------|--------|------------------------------|
| 0    | version     | uint8  | 1                            |
| 1-2  | seq         | uint16 | counter, wraps at 65535      |
| 3-4  | mean speed  | uint16 | x 0.01 m/s                   |
| 5-6  | gust        | uint16 | x 0.01 m/s                   |
| 7-8  | mean dir    | uint16 | x 0.1 deg (vector average)   |
| 9    | std speed   | uint8  | x 0.05 m/s                   |
| 10-11| temperature | int16  | x 0.01 C, -32768 = n/a       |
| 12   | battery     | uint8  | 2.00 V + 0.01 V x value      |
| 13   | flags       | uint8  | bit0 range, 1 stuck, 2 spike, 3 low batt, 4 calib due, 5 fault, 6 few samples |

Why fixed-point integers: LoRaWAN payloads must stay tiny (airtime = battery),
and floats would waste 4 bytes each. 0.01 m/s resolution keeps the
below-1 m/s range (the critical one for urban ventilation) usable.

Both sides must share the scaling constants:
`firmware/include/config.h` <-> `server/uwsn/config.py`.
