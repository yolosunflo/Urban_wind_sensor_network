"""Dashboard helpers that turn stored measurements into what the page shows.
Pure pandas, no Streamlit here, so everything can be tested without a browser."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

from uwsn.analysis import Analyzer, compass_angle, vector_mean_direction, wind_components
from uwsn.config import SETTINGS
from uwsn.models import QualityFlag

# Same flags as Measurement.is_usable: the wind value cannot be trusted
UNRELIABLE_WIND = int(QualityFlag.SPIKE | QualityFlag.OUT_OF_RANGE | QualityFlag.STUCK |
                      QualityFlag.SENSOR_FAULT | QualityFlag.DRIFT_SUSPECTED)

ONLINE_MAX_AGE = timedelta(minutes=3 * SETTINGS.window_s // 60)      # 3 missed windows = 30 min
DELAYED_MAX_AGE = timedelta(hours=3)
CALIBRATION_WARNING_DAYS = 30
LOCAL_TZ = "Europe/Zurich"          # Swiss time (Lausanne too); time zone for "hour of day" and "day" (data itself is stored in UTC)


def flag_text(value: int) -> str:
    """Readable list of the flags set in a measurement, e.g. 'Spike, Low battery'."""
    names = [f.name.replace("_", " ").capitalize() for f in QualityFlag if f and value & f]
    return ", ".join(names) or "OK"


def humanize_age(age: timedelta) -> str:
    minutes = int(age.total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} h ago"
    return f"{hours // 24} d {hours % 24} h ago"


# ---------------------------------------------------------------- time series

def series_frames(df_all: pd.DataFrame, flagged_mode: str, window_s: int = SETTINGS.window_s):
    """Prepare 10-minute data for the line charts.

    flagged_mode  "hide"    unreliable values are removed (the line breaks there)
                  "grey"    same lines, plus the unreliable values as separate grey points
                  "show"    everything is drawn like normal data
    Returns (lines, flagged). `lines` has columns device_id, ts, mean_speed_ms, gust_ms, temp_c
    and an empty (NaN) row inside every gap of missing packets, so charts do not draw a line
    across the gap. `flagged` maps each column to the rows that were hidden (empty unless "grey").
    """
    cols = ["mean_speed_ms", "gust_ms", "temp_c"]
    d = df_all.sort_values(["device_id", "ts"]).copy()
    wind_bad = (d["flags"] & UNRELIABLE_WIND) != 0
    temp_bad = ((d["flags"] & int(QualityFlag.TEMP_FAULT)) != 0) | d["temp_c"].isna()
    d["flags_text"] = d["flags"].map(flag_text)

    flagged = {c: d.iloc[0:0] for c in cols}
    if flagged_mode != "show":
        if flagged_mode == "grey":
            flagged = {"mean_speed_ms": d[wind_bad], "gust_ms": d[wind_bad],
                       "temp_c": d[(d["flags"] & int(QualityFlag.TEMP_FAULT) != 0) & d["temp_c"].notna()]}
        d.loc[wind_bad, ["mean_speed_ms", "gust_ms"]] = np.nan
        d.loc[temp_bad, "temp_c"] = np.nan
    return insert_gaps(d[["device_id", "ts"] + cols], window_s), flagged


def insert_gaps(df: pd.DataFrame, window_s: int = SETTINGS.window_s) -> pd.DataFrame:
    """Add an all-NaN row just after the last message before every gap longer than 1.5 windows."""
    d = df.sort_values(["device_id", "ts"])
    gap_start = d.groupby("device_id")["ts"].shift(-1) - d["ts"] > pd.Timedelta(seconds=1.5 * window_s)
    filler = d.loc[gap_start, ["device_id", "ts"]]
    filler = filler.assign(ts=filler["ts"] + pd.Timedelta(seconds=window_s))
    return pd.concat([d, filler]).sort_values(["device_id", "ts"], kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------- map over time

STEP_CHOICES_H = (1, 2, 3, 6, 12, 24)


def map_steps(hourly: pd.DataFrame, max_steps: int = 300) -> tuple[pd.DataFrame, int]:
    """Wind per sensor for each step of the map slider.

    Hourly values are grouped into steps of 1, 2, 3, 6, 12 or 24 hours: the smallest step that
    gives at most `max_steps` steps (keeps the figure light for long periods).
    Returns (table, step_hours); table columns: step_ts, device_id, mean_speed_ms, gust_ms, direction.
    Direction is the speed-weighted vector mean. Steps without data for a sensor have no row."""
    cols = ["step_ts", "device_id", "mean_speed_ms", "gust_ms", "direction"]
    d = hourly.dropna(subset=["mean_speed_ms"])
    if d.empty:
        return pd.DataFrame(columns=cols), 1
    n_hours = (d["ts"].max() - d["ts"].min()) / pd.Timedelta(hours=1) + 1
    step = next((s for s in STEP_CHOICES_H if n_hours / s <= max_steps), STEP_CHOICES_H[-1])
    d = d.assign(step_ts=d["ts"].dt.floor(f"{step}h"))
    d["_x"], d["_y"] = wind_components(d["mean_speed_ms"], d["mean_dir_deg"].fillna(0))
    d.loc[d["mean_dir_deg"].isna(), ["_x", "_y"]] = np.nan
    out = d.groupby(["step_ts", "device_id"]).agg(
        mean_speed_ms=("mean_speed_ms", "mean"), gust_ms=("gust_ms", "max"),
        _x=("_x", "mean"), _y=("_y", "mean"))
    out["direction"] = compass_angle(out.pop("_x"), out.pop("_y"))
    return out.reset_index()[cols], step


# ---------------------------------------------------------------- mean speed over time
# All three take Analyzer.hourly() (reliable data only) and use local time, so the daily
# cycle lines up with the real day (afternoon peak, calm night).

def _with_local_time(hourly: pd.DataFrame) -> pd.DataFrame:
    d = hourly.dropna(subset=["mean_speed_ms"]).copy()
    local = d["ts"].dt.tz_convert(LOCAL_TZ)
    d["hour"], d["day"] = local.dt.hour, local.dt.tz_localize(None).dt.normalize()
    return d


def daily_cycle(hourly: pd.DataFrame) -> pd.DataFrame:
    """Mean speed for each hour of the day (0-23), per sensor. Columns: device_id, hour, mean_speed_ms."""
    d = _with_local_time(hourly)
    return d.groupby(["device_id", "hour"], as_index=False)["mean_speed_ms"].mean()


def daily_mean(hourly: pd.DataFrame) -> pd.DataFrame:
    """Mean speed per calendar day, per sensor, plus a 'Network' row per day (mean of the sensors).
    Columns: device_id, day, mean_speed_ms."""
    d = _with_local_time(hourly)
    per_sensor = d.groupby(["device_id", "day"], as_index=False)["mean_speed_ms"].mean()
    network = per_sensor.groupby("day", as_index=False)["mean_speed_ms"].mean().assign(device_id="Network")
    return pd.concat([per_sensor, network], ignore_index=True)


def hour_by_day(hourly: pd.DataFrame) -> pd.DataFrame:
    """Network mean speed: one row per hour of the day (0-23), one column per day."""
    d = _with_local_time(hourly)
    return (d.groupby(["hour", "day"])["mean_speed_ms"].mean().unstack("day")
             .reindex(range(24)))


# ---------------------------------------------------------------- per-sensor tables

def sensor_summary(df_ok: pd.DataFrame, df_all: pd.DataFrame, sensors: pd.DataFrame,
                   device_ids: list[str], low_wind_ms: float) -> pd.DataFrame:
    """One row per selected sensor with the key numbers of the selected period.
    Statistics use usable data only (df_ok); availability counts every received window."""
    a_ok, a_all = Analyzer(df_ok), Analyzer(df_all)
    meta = sensors.set_index("device_id") if not sensors.empty else pd.DataFrame(
        columns=["lat", "lon", "height_m", "site_description"])
    out = pd.DataFrame(index=pd.Index(device_ids, name="device_id"))
    out["site"] = meta["site_description"].reindex(out.index).fillna("")
    out["lat"] = meta["lat"].reindex(out.index)
    out["lon"] = meta["lon"].reindex(out.index)
    if df_ok.empty:
        for c in ["mean_speed", "max_gust", "direction", "low_wind", "mean_temp", "wind_temp_corr"]:
            out[c] = np.nan
    else:
        g = df_ok.groupby("device_id")
        out["mean_speed"] = g["mean_speed_ms"].mean()
        out["max_gust"] = g["gust_ms"].max()
        out["direction"] = pd.Series({k: vector_mean_direction(x["mean_speed_ms"], x["mean_dir_deg"])
                                      for k, x in g})
        out["low_wind"] = a_ok.low_wind_fraction(low_wind_ms)
        temp_ok = df_ok[(df_ok["flags"] & int(QualityFlag.TEMP_FAULT)) == 0]
        out["mean_temp"] = temp_ok.groupby("device_id")["temp_c"].mean()
        out["wind_temp_corr"] = a_ok.wind_temperature_correlation()
    out["availability"] = a_all.availability()
    out["usable_share"] = (df_ok.groupby("device_id").size() /
                           df_all.groupby("device_id").size()) if not df_all.empty else np.nan
    return out


def network_health(df_everything: pd.DataFrame, sensors: pd.DataFrame, device_ids: list[str],
                   availability: pd.Series, now: Optional[datetime] = None) -> pd.DataFrame:
    """Current state of each selected sensor.

    `df_everything` must hold all stored data (not the date-filtered part): last seen, battery
    and calibration describe the sensor NOW, whatever period the user is looking at."""
    now = now or datetime.now(timezone.utc)
    meta = sensors.set_index("device_id") if not sensors.empty else pd.DataFrame()
    latest = (df_everything.sort_values("ts").groupby("device_id").tail(1).set_index("device_id")
              if not df_everything.empty else pd.DataFrame())
    rows = []
    for dev in device_ids:
        row = {"device_id": dev, "site": "", "status": "No data", "last_seen": pd.NaT,
               "last_seen_text": "never", "battery_v": np.nan, "low_battery": False,
               "availability": availability.get(dev, np.nan), "calibration": "Unknown",
               "calibration_due": False}
        if dev in meta.index:
            row["site"] = meta.at[dev, "site_description"] or ""
        installed = _installed_at(meta, dev)
        if dev in latest.index:
            last = latest.loc[dev]
            age = now - last["ts"].to_pydatetime()
            row.update(
                last_seen=last["ts"], last_seen_text=humanize_age(age),
                status="Online" if age <= ONLINE_MAX_AGE else
                       "Delayed" if age <= DELAYED_MAX_AGE else "Offline",
                battery_v=last["battery_v"],
                low_battery=bool(last["battery_v"] < SETTINGS.low_battery_v or
                                 int(last["flags"]) & QualityFlag.LOW_BATTERY))
            flag_due = bool(int(last["flags"]) & QualityFlag.CALIBRATION_DUE)
        else:
            flag_due = False
        row["calibration"], row["calibration_due"] = _calibration_state(installed, flag_due, now)
        rows.append(row)
    return pd.DataFrame(rows)


def _installed_at(meta: pd.DataFrame, dev: str):
    if dev in meta.index and "installed_at" in meta.columns and pd.notna(meta.at[dev, "installed_at"]):
        t = pd.Timestamp(meta.at[dev, "installed_at"])
        return t if t.tzinfo else t.tz_localize("UTC")
    return None


def _calibration_state(installed, flag_due: bool, now: datetime) -> tuple[str, bool]:
    """Due if the node says so, or if the recalibration interval since installation has passed."""
    if installed is not None:
        days_left = (installed + pd.Timedelta(days=SETTINGS.recalibration_days) - now).days
        if flag_due or days_left < 0:
            return "Due", True
        return (f"Due in {days_left} d", False) if days_left <= CALIBRATION_WARNING_DAYS else ("OK", False)
    return ("Due", True) if flag_due else ("Unknown", False)


def attention_items(health: pd.DataFrame) -> list[str]:
    """Markdown lines (with colour and icon) for everything in the network that needs a person."""
    items = []
    for r in health.itertuples():
        name = f"**{r.device_id.split('-')[-1]}**" + (f" {r.site.split(',')[0]}" if r.site else "")
        if r.status == "Offline":
            items.append(f":red[:material/wifi_off:] {name} is offline, last message {r.last_seen_text}.")
        elif r.status == "Delayed":
            items.append(f":orange[:material/schedule:] {name} is late, last message {r.last_seen_text}.")
        if r.low_battery and pd.notna(r.battery_v):
            items.append(f":orange[:material/battery_alert:] {name} has a low battery ({r.battery_v:.2f} V).")
        if r.calibration_due:
            items.append(f":orange[:material/tune:] {name} needs recalibration.")
    return items


# ---------------------------------------------------------------- export

def export_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Measurements with readable columns added, for the CSV download."""
    out = df.copy()
    out["usable"] = (out["flags"] & UNRELIABLE_WIND) == 0
    out["flags_text"] = out["flags"].map(flag_text)
    out["ts"] = out["ts"].map(lambda t: t.isoformat())
    return out
