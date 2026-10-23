"""Central configuration. Secrets come from environment variables, never from git."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # TTN (The Things Network) MQTT
    ttn_host: str = os.getenv("TTN_HOST", "eu1.cloud.thethings.network")
    ttn_port: int = 8883
    ttn_app_id: str = os.getenv("TTN_APP_ID", "")
    ttn_api_key: str = os.getenv("TTN_API_KEY", "")

    db_path: str = os.getenv("UWSN_DB", "uwsn.sqlite")

    # Payload scaling: MUST match firmware/include/config.h
    speed_lsb_ms: float = 0.01
    dir_lsb_deg: float = 0.1
    std_lsb_ms: float = 0.05
    temp_lsb_c: float = 0.01
    battery_offset_v: float = 2.0
    battery_lsb_v: float = 0.01

    window_s: int = 600            # expected interval between uplinks
    max_speed_ms: float = 60.0
    max_jump_ms: float = 15.0      # spike threshold between consecutive windows
    stuck_windows: int = 6         # identical values -> sensor stuck
    low_battery_v: float = 3.3
    recalibration_days: int = 180


SETTINGS = Settings()
