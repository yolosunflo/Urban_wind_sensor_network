"""SQLite persistence. Swap for PostgreSQL/TimescaleDB if the network grows."""
import sqlite3
from typing import Iterable, Optional
import pandas as pd
from .models import Measurement, SensorMeta, Uplink

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sensors(
  device_id TEXT PRIMARY KEY, lat REAL, lon REAL, height_m REAL,
  site_description TEXT, installed_at TEXT);
CREATE TABLE IF NOT EXISTS uplinks(
  id INTEGER PRIMARY KEY, device_id TEXT, received_at TEXT,
  payload BLOB, rssi REAL, snr REAL);
CREATE TABLE IF NOT EXISTS measurements(
  device_id TEXT, ts TEXT, seq INTEGER, mean_speed_ms REAL, gust_ms REAL,
  mean_dir_deg REAL, std_speed_ms REAL, temp_c REAL, battery_v REAL, flags INTEGER,
  PRIMARY KEY(device_id, ts));
"""


class Repository:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(_SCHEMA)

    def save_sensor(self, s: SensorMeta) -> None: ...          # TODO
    def save_uplink(self, u: Uplink) -> None: ...              # TODO: keep raw bytes for replay

    def save_measurement(self, m: Measurement) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO measurements VALUES (?,?,?,?,?,?,?,?,?,?)",
            (m.device_id, m.ts.isoformat(), m.seq, m.mean_speed_ms, m.gust_ms,
             m.mean_dir_deg, m.std_speed_ms, m.temp_c, m.battery_v, int(m.flags)))
        self._db.commit()

    def load_measurements(self, device_ids: Optional[Iterable[str]] = None,
                          start: Optional[str] = None, end: Optional[str] = None,
                          usable_only: bool = False) -> pd.DataFrame:
        """TODO: build the WHERE clause from the arguments."""
        return pd.read_sql("SELECT * FROM measurements", self._db, parse_dates=["ts"])

    def load_sensors(self) -> pd.DataFrame:
        return pd.read_sql("SELECT * FROM sensors", self._db)
