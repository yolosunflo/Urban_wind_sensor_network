"""
SQLite database in uwsn.sqlite
Three tables: sensors (informations about the sensors), uplinks (the raw data to 
re-decode or re-validate everything later if a bug happens), measurements (one row per 
sensor, in physical unit)
"""
import sqlite3
from datetime import date, datetime
from typing import Iterable, Optional, Union
import pandas as pd
from .models import Measurement, QualityFlag, SensorMeta, Uplink, UNUSABLE_WIND_MASK

# start / end can be an ISO string ("2026-11-01"), a date or a datetime
TimeBound = Union[str, date, datetime]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sensors(
  device_id TEXT PRIMARY KEY, 
  lat REAL, lon REAL, 
  height_m REAL,
  site_description TEXT, 
  installed_at TEXT);
CREATE TABLE IF NOT EXISTS uplinks(
  id INTEGER PRIMARY KEY, 
  device_id TEXT, 
  received_at TEXT,
  payload BLOB, 
  rssi REAL, 
  snr REAL);
CREATE TABLE IF NOT EXISTS measurements(
  device_id TEXT, 
  ts TEXT, 
  seq INTEGER, 
  mean_speed_ms REAL, 
  gust_ms REAL,
  mean_dir_deg REAL, 
  std_speed_ms REAL, 
  temp_c REAL, 
  battery_v REAL, 
  flags INTEGER,
  PRIMARY KEY(device_id, ts));
"""


class Repository:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(_SCHEMA)

    def save_sensor(self, s: SensorMeta) -> None:
        """Insert a sensor, or update it if the device_id already exists."""
        self._db.execute(
            "INSERT OR REPLACE INTO sensors VALUES (?,?,?,?,?,?)",
            (s.device_id, s.lat, s.lon, s.height_m, s.site_description,
             s.installed_at.isoformat() if s.installed_at else None))
        self._db.commit()

    def save_uplink(self, u: Uplink) -> None:
        """
        Log of everything received, it keeps every message, even duplicates and broken ones.
        No id needed: we don’t pass one, so SQLite numbers the rows by itself (1, 2, 3…).
        """
        self._db.execute(
            "INSERT INTO uplinks(device_id, received_at, payload, rssi, snr) VALUES (?,?,?,?,?)",
            (u.device_id, u.received_at.isoformat(), u.payload, u.rssi, u.snr))
        self._db.commit()

    def save_measurement(self, m: Measurement) -> None:
        """
        Insert a sensor, or update it if the device_id already exists.
        If TTN delivers the same message twice, the second copy replaces the first 
        instead of creating a duplicate.
        """
        self._db.execute(
            "INSERT OR REPLACE INTO measurements VALUES (?,?,?,?,?,?,?,?,?,?)",
            (m.device_id, m.ts.isoformat(), m.seq, m.mean_speed_ms, m.gust_ms,
             m.mean_dir_deg, m.std_speed_ms, m.temp_c, m.battery_v, int(m.flags)))
        self._db.commit()

    def load_measurements(self, device_ids: Optional[Iterable[str]] = None,
                          start: Optional[TimeBound] = None, end: Optional[TimeBound] = None,
                          usable_only: bool = False) -> pd.DataFrame:
        """
        Measurements, one row per sensor per window, ordered by sensor then time.

        device_ids   None = all sensors; an empty list = no sensor (empty result).
        start / end  start is inclusive, end is EXCLUSIVE (so a whole day is [day, day + 1)).
        usable_only  drop rows carrying a flag that makes the wind data unreliable.
        """
        where, params = [], []
        if device_ids is not None:
            ids = list(device_ids)
            where.append(f"device_id IN ({','.join('?' * len(ids))})")
            params += ids
        if start is not None:
            where.append("ts >= ?")
            params.append(_iso(start))
        if end is not None:
            where.append("ts < ?")
            params.append(_iso(end))
        if usable_only:
            where.append("(flags & ?) = 0")
            params.append(int(UNUSABLE_WIND_MASK))
        sql = "SELECT * FROM measurements"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY device_id, ts"
        return pd.read_sql(sql, self._db, params=params, parse_dates={"ts": {"format": "ISO8601", "utc": True}})

    def load_sensors(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM sensors", self._db)


def _iso(t: TimeBound) -> str:
    return t if isinstance(t, str) else t.isoformat()
