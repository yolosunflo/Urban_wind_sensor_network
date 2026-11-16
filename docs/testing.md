# Testing

`pio` commands run from the **project root** (where `platformio.ini` is).
Python commands run from **`server/`**.
Each test file explains itself at the top: this page only says what to run and when.

## 0. Setup (once per computer)

1. Install **VS Code** and its **PlatformIO IDE** extension. Wait until it finishes installing
   (messages bottom right, a few minutes), then restart VS Code.
2. Open the **whole project folder** (*File -> Open Folder* -> `Urban_wind_sensor_network`).
3. Make the `pio` command available in the terminal (otherwise: "command not found: pio"):
   - macOS:
     ```
     echo 'export PATH="$HOME/.platformio/penv/bin:$PATH"' >> ~/.zshrc
     ```
     If it says `permission denied: .../.zshrc`, first run `sudo chown $(whoami) ~/.zshrc`
     (asks for your Mac password, nothing shows while typing), then the line above again.
   - Linux: same line with `~/.bashrc` instead of `~/.zshrc`.
   - Windows: Start -> "Edit environment variables for your account" -> *Path* -> *Edit* ->
     *New* -> `%USERPROFILE%\.platformio\penv\Scripts` -> OK, then restart VS Code.

   Close the terminal, open a new one, and check: `pio --version` prints a version.
   (Shortcut without this step: PlatformIO icon -> *Quick Access* -> *Miscellaneous* ->
   *PlatformIO Core CLI* opens a terminal where `pio` works.)
4. Install a C++ compiler: macOS `xcode-select --install`, Linux `sudo apt install g++`,
   Windows MSYS2 (https://www.msys2.org) then `pacman -S mingw-w64-ucrt-x86_64-gcc`
   and add `C:\msys64\ucrt64\bin` to *Path* as above.

## 1. Without hardware

| Command | Checks |
|---|---|
| `pio test -e native` | node logic on the computer: calibration, quality flags, bytes, downlinks |
| `cd server` then `python -m pytest` | the whole server, plus `test_end_to_end.py`: the real node code fed with fake values, through the whole server and back |
| `pio run -e node` (and `-e test_i2c`, ...) | the code compiles for the LoRa-E5 (no board needed, nothing uploaded) |

To play with a simulated node by hand: `firmware/tools/node_sim.cpp` (instructions inside).

## 2. Safety rules

1. **Antenna always on** before powering the board or the gateway: transmitting without it can destroy the radio.
2. **One power source at a time:** USB on the desk, battery outdoors, never both.
3. With the ST-Link on a USB-powered board, connect only **GND, DIO, CLK, RST** (not 3V3).

## 3. First time with a board

1. Install **STM32CubeProgrammer** (st.com).
2. Connect the ST-Link to the board: DIO, CLK, RST, GND.
3. Remove the factory lock: CubeProgrammer -> ST-LINK, mode *Under reset* -> *Connect* ->
   *OB* tab -> *Read Out Protection* -> **RDP = AA** -> *Apply*. Without this, uploads fail.
4. For the radio: copy `firmware/include/secrets.example.h` to `secrets.h` and fill it from TTN.

## 4. Hardware tests

```
pio run -e <test> -t upload     # upload
pio device monitor              # read the output, Ctrl+C to quit
```

Do them in order. `[ OK ]` / `[FAIL]` lines give the result.

| Test | Connect | OK if | If not |
|---|---|---|---|
| `test_board` | antenna, USB, ST-Link | supply 3.2-3.4 V, counter keeps going through deep sleeps | nothing printed: lock still on, or use `Serial1` in `bringup.h` |
| `test_i2c` | AS5600 + TMP102 on SDA PA15, SCL PB15 | `0x36` and `0x48` found | SDA/SCL swapped, no power, no pull-ups |
| `test_temperature` | TMP102 | within 0.5 C of a thermometer | run `test_i2c` |
| `test_as5600` | AS5600 + vane | `magnet OK`, angle smooth 0-360 deg | magnet too far / close / off-centre |
| `test_reed` | reed switch PB4 to GND | one turn = one pulse per magnet | double pulses: raise `REED_DEBOUNCE_US` |
| `test_battery` | divider on PB3 | matches a multimeter within 0.05 V | fix `BATTERY_DIVIDER` in `config.h` |
| `test_radio` | antenna, `secrets.h`, gateway online | `join OK`, messages in TTN *Live data* | keys, gateway, or node too close (> 2 m) |
| `test_bench` | everything | one CSV line per second | — |

**Note while testing:** the angle when the vane points north (direction offset) and the
temperature difference from the thermometer (temperature offset). They are sent to the node
by downlink later; never put them in the code.

**Calibration bench:** `pio device monitor > bench.csv` with `test_bench`, note the reference
speed at each fan step, then on the server use `check_drift()`, `corrected_speed_params()`,
`build_downlink()` and `send_downlink()`.

**Real firmware:** for a quick try, set `WINDOW_S 60` / `BURST_S 30` in `config.h` and
`window_s = 60` in `server/uwsn/config.py`, then `pio run -e node -t upload`.
Put back 600 / 300 / 600 after.

## 5. Gateway (ThinkNode G1)

1. Antenna on, power, hold the setup button 5 s (slow blue blink), open its web page.
2. Internet: Ethernet, a phone hotspot or a home Wi-Fi (eduroam usually does not work).
3. TTN console -> *Register gateway*: its Gateway EUI, plan *Europe 863-870 MHz (SF9 for RX2)*.
4. Gateway web page: *Packet forwarder*, server `eu1.cloud.thethings.network`, port 1700.

## 6. Register the sensors

```
cd server
cp sensors.example.csv sensors.csv        # one line per node, device_id = TTN End device ID
python scripts/register_sensors.py sensors.csv --list
```
