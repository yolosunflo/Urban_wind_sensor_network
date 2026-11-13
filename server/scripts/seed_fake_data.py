"""Fill a local SQLite database with realistic FAKE data, to develop the dashboard without hardware.

    cd server
    python scripts/seed_fake_data.py              # creates uwsn.sqlite (3 weeks, 7 sensors in Lausanne)
    python scripts/seed_fake_data.py --force      # replace an existing database
    python scripts/seed_fake_data.py --db /tmp/test.sqlite --days 7 --seed 1

The data goes through the real DataValidator, so the quality flags are the ones the server
would really set. Some sensors are deliberately broken so every dashboard state can be tested:

    uwsn-01  Flon, street canyon        calm, wind channelled along the street
    uwsn-02  Ouchy, lake promenade      windy and open; short SENSOR_FAULT (zeros) on day 8
    uwsn-03  Place Saint-Francois       wind SPIKES, a few temperature faults
    uwsn-04  Sauvabelin, park edge      STUCK sensor for 4 hours
    uwsn-05  Pontaise, school courtyard lost packets (random + two long outages), a few FEW_SAMPLES
    uwsn-06  CHUV, rooftop              LOW BATTERY for the last days + CALIBRATION DUE
    uwsn-07  Vidy, lakeside path        stopped sending 3 days ago
"""
import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # so "import uwsn" works

from uwsn.config import SETTINGS                                   # noqa: E402
from uwsn.models import Measurement, QualityFlag, SensorMeta       # noqa: E402
from uwsn.storage import Repository                                # noqa: E402
from uwsn.validation import DataValidator                          # noqa: E402

STEP = timedelta(seconds=SETTINGS.window_s)
LOCAL_UTC_OFFSET_H = 1                      # Swiss winter time: only used for the daily cycle


@dataclass
class Site:
    device_id: str
    description: str
    lat: float
    lon: float
    height_m: float
    speed_factor: float                     # local mean wind relative to the regional wind
    turbulence: float                       # std / mean speed
    temp_offset_c: float                    # urban heat island
    canyon_axis_deg: Optional[float] = None  # street direction, wind is channelled along it
    canyon_strength: float = 0.0            # 0 = open, 1 = strongly channelled
    installed_days_before_start: int = 60
    battery_start_v: float = 3.95
    battery_slope_v_per_day: float = 0.004


SITES = [
    Site("uwsn-01", "Flon, narrow street canyon", 46.5216, 6.6255, 4, 0.60, 0.35, 1.2,
         canyon_axis_deg=70, canyon_strength=0.8, installed_days_before_start=90),
    Site("uwsn-02", "Ouchy, open lake promenade", 46.5075, 6.6265, 4, 1.35, 0.22, -0.4,
         installed_days_before_start=150),
    Site("uwsn-03", "Place Saint-François, city square", 46.5193, 6.6333, 5, 0.95, 0.30, 0.8,
         installed_days_before_start=75),
    Site("uwsn-04", "Sauvabelin, park edge", 46.5340, 6.6540, 3, 1.00, 0.30, -0.2,
         installed_days_before_start=120),
    Site("uwsn-05", "School courtyard, Pontaise", 46.5330, 6.6285, 3, 0.40, 0.40, 0.5,
         installed_days_before_start=45),
    Site("uwsn-06", "CHUV, rooftop reference", 46.5252, 6.6411, 25, 1.50, 0.18, 0.0,
         installed_days_before_start=200, battery_start_v=3.62, battery_slope_v_per_day=0.0188),
    Site("uwsn-07", "Vidy, lakeside path", 46.5130, 6.5900, 3, 0.85, 0.28, 0.1,
         canyon_axis_deg=60, canyon_strength=0.5, installed_days_before_start=100,
         battery_start_v=3.72, battery_slope_v_per_day=0.0165),
]


# ---------------------------------------------------------------- weather model

def ar1(rng, n, tau_windows):
    """Smooth random series with mean 0 and std 1; tau = how many windows it 'remembers'."""
    phi = np.exp(-1 / tau_windows)
    e = rng.normal(size=n) * np.sqrt(1 - phi ** 2)
    x = np.empty(n)
    x[0] = rng.normal()
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def angle_diff(a, b):
    """Signed smallest difference a - b in degrees, in [-180, 180)."""
    return (a - b + 180) % 360 - 180


class Weather:
    """Regional weather shared by all sensors (they are in the same city)."""

    def __init__(self, rng, times):
        n = len(times)
        hour = np.array([(t.hour + t.minute / 60 + LOCAL_UTC_OFFSET_H) % 24 for t in times])
        doy = np.array([t.timetuple().tm_yday for t in times])

        synoptic = ar1(rng, n, 12 * 6 * 2)                           # fronts: ~1 day memory
        diurnal_wind = 1 + 0.35 * np.sin(2 * np.pi * (hour - 9) / 24)  # peak at 15:00
        self.speed = np.clip(2.4 + 1.1 * synoptic, 0.3, None) * diurnal_wind

        regime = ar1(rng, n, 24 * 6 * 2)                              # SW wind most of the time,
        blend = 1 / (1 + np.exp(-3 * (regime + 0.9)))                 # sometimes a NE episode
        self.direction = (50 + 180 * blend + rng.normal(0, 15, n)) % 360

        seasonal = 10 - 9 * np.cos(2 * np.pi * (doy - 15) / 365)
        diurnal_temp = 3.0 * np.sin(2 * np.pi * (hour - 9) / 24)      # peak at 15:00
        self.temp = seasonal + diurnal_temp + 2.5 * ar1(rng, n, 24 * 6 * 2)


def simulate_site(rng, site: Site, weather: Weather, times):
    """Return arrays (speed, gust, direction, std, temp, battery) before any fault is injected."""
    n = len(times)
    reg_speed, reg_dir = weather.speed, weather.direction

    direction = reg_dir.copy()
    speed = reg_speed * site.speed_factor
    if site.canyon_axis_deg is not None:
        # the wind is pulled towards the street axis (either way along it) ...
        to_axis = angle_diff(site.canyon_axis_deg, reg_dir)
        to_axis = np.where(np.abs(to_axis) > 90, angle_diff(site.canyon_axis_deg + 180, reg_dir), to_axis)
        direction = reg_dir + site.canyon_strength * to_axis
        # ... and wind blowing across the street is slowed down
        cross = np.abs(np.sin(np.deg2rad(angle_diff(reg_dir, site.canyon_axis_deg))))
        speed = speed * (1 - 0.35 * site.canyon_strength * cross)

    speed = speed * np.exp(0.18 * ar1(rng, n, 3) + rng.normal(0, 0.08, n))      # local gustiness
    speed = np.clip(speed, 0, None)
    direction = (direction + rng.normal(0, 1, n) * (10 + 35 / (1 + speed))) % 360   # noisy in calm air

    std = site.turbulence * speed + 0.05 + np.abs(rng.normal(0, 0.05, n))
    gust = speed + rng.uniform(1.8, 3.0, n) * std

    temp = (weather.temp + site.temp_offset_c - 0.2 * (speed - speed.mean())
            + rng.normal(0, 0.15, n))

    days = np.arange(n) * SETTINGS.window_s / 86400
    hour = np.array([(t.hour + t.minute / 60 + LOCAL_UTC_OFFSET_H) % 24 for t in times])
    battery = (site.battery_start_v - site.battery_slope_v_per_day * days
               + 0.03 * np.clip(np.sin(2 * np.pi * (hour - 6) / 24), 0, None)      # solar ripple
               + rng.normal(0, 0.004, n))
    return speed, gust, direction, std, temp, battery


# ---------------------------------------------------------------- faults

def window_range(times, start_h_from_end, duration_h):
    """Indices of the windows that start `start_h_from_end` hours before the end, for `duration_h`."""
    n = len(times)
    first = n - int(start_h_from_end * 3600 / SETTINGS.window_s)
    return slice(max(first, 0), max(first + int(duration_h * 3600 / SETTINGS.window_s), 0))


def build_site(rng, site: Site, weather: Weather, times):
    """Return (list of Measurement before validation, mask of windows that were never received)."""
    n = len(times)
    speed, gust, direction, std, temp, battery = simulate_site(rng, site, weather, times)
    temp = temp.astype(object)
    flags = np.zeros(n, dtype=int)
    lost = np.zeros(n, dtype=bool)
    days = n * SETTINGS.window_s / 86400

    if site.device_id == "uwsn-02":                                  # bearing failure: zeros
        sl = window_range(times, 0.4 * days * 24, 2)
        speed[sl], gust[sl], std[sl] = 0.0, 0.0, 0.0
        flags[sl] |= QualityFlag.SENSOR_FAULT

    if site.device_id == "uwsn-03":
        for i in rng.choice(np.arange(200, n - 50), size=6, replace=False):     # electrical spikes
            speed[i] = rng.uniform(28, 38)
            gust[i] = speed[i] + rng.uniform(2, 5)
        sl = window_range(times, 0.55 * days * 24, 5)                # temperature probe drops out
        temp[sl] = None
        sl = window_range(times, 0.30 * days * 24, 1)                # ... and reads nonsense
        temp[sl] = 85.0

    if site.device_id == "uwsn-04":                                  # anemometer frozen at one value
        sl = window_range(times, 0.45 * days * 24, 4)
        speed[sl], gust[sl], std[sl] = 1.7, 2.4, 0.1
        direction[sl] = 212.0

    if site.device_id == "uwsn-05":
        lost |= rng.random(n) < 0.06                                 # radio shadows, random
        lost[window_range(times, 0.62 * days * 24, 9)] = True        # long outage 1
        lost[window_range(times, 0.20 * days * 24, 3)] = True        # long outage 2
        flags[rng.random(n) < 0.01] |= QualityFlag.FEW_SAMPLES

    if site.device_id == "uwsn-06":
        flags |= QualityFlag.CALIBRATION_DUE                         # set by the firmware

    if site.device_id == "uwsn-07":                                  # node died 3 days 4 hours ago
        lost[n - int(76 * 3600 / SETTINGS.window_s):] = True

    # quantise like the real payload (see Settings.*_lsb), and keep the direction in [0, 360)
    q = SETTINGS
    speed = np.round(speed / q.speed_lsb_ms) * q.speed_lsb_ms
    gust = np.maximum(np.round(gust / q.speed_lsb_ms) * q.speed_lsb_ms, speed)
    direction = np.round(direction / q.dir_lsb_deg) * q.dir_lsb_deg % 360
    std = np.round(std / q.std_lsb_ms) * q.std_lsb_ms
    battery = np.round(battery / q.battery_lsb_v) * q.battery_lsb_v

    out = []
    for i in range(n):
        if lost[i]:
            continue
        t = temp[i]
        out.append(Measurement(
            device_id=site.device_id, ts=times[i], seq=i % 65536,     # seq counts lost windows too
            mean_speed_ms=round(float(speed[i]), 2), gust_ms=round(float(gust[i]), 2),
            mean_dir_deg=round(float(direction[i]), 1), std_speed_ms=round(float(std[i]), 2),
            temp_c=None if t is None else round(float(t), 2),
            battery_v=round(float(battery[i]), 2), flags=QualityFlag(int(flags[i]))))
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=SETTINGS.db_path, help="database file (default: %(default)s)")
    ap.add_argument("--days", type=int, default=21, help="how many days of data (default: %(default)s)")
    ap.add_argument("--seed", type=int, default=42, help="random seed: same seed = same data")
    ap.add_argument("--force", action="store_true", help="replace the database if it already exists")
    args = ap.parse_args()

    db = Path(args.db)
    if db.exists():
        if not args.force:
            sys.exit(f"{db} already exists. Use --force to replace it (this deletes its content).")
        db.unlink()

    rng = np.random.default_rng(args.seed)
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end -= timedelta(minutes=end.minute % 10)
    n = args.days * 24 * 3600 // SETTINGS.window_s
    times = [end - STEP * (n - 1 - i) for i in range(n)]
    start = times[0]
    weather = Weather(rng, times)

    repo = Repository(str(db))
    validator = DataValidator()
    print(f"Writing {db} ({args.days} days up to {end:%Y-%m-%d %H:%M} UTC)")
    for site in SITES:
        repo.save_sensor(SensorMeta(
            site.device_id, site.lat, site.lon, site.height_m, site.description,
            installed_at=start - timedelta(days=site.installed_days_before_start)))
        rows = [validator.validate(m) for m in build_site(rng, site, weather, times)]
        for m in rows:
            repo.save_measurement(m)
        names = {f.name: sum(1 for m in rows if m.flags & f) for f in QualityFlag if f}
        names = ", ".join(f"{k}={v}" for k, v in names.items() if v)
        print(f"  {site.device_id}: {len(rows):5d}/{n} windows   {names or 'no flags'}")


if __name__ == "__main__":
    main()
