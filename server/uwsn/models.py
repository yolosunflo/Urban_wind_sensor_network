"""Data classes shared by every module. Pure data, no logic."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntFlag
from typing import Optional


class QualityFlag(IntFlag):
    """Bits 0-6 mirror the firmware flags, bits 8+ are added by the server."""
    OK = 0
    OUT_OF_RANGE = 1 << 0
    STUCK = 1 << 1
    SPIKE = 1 << 2
    LOW_BATTERY = 1 << 3
    CALIBRATION_DUE = 1 << 4
    SENSOR_FAULT = 1 << 5
    FEW_SAMPLES = 1 << 6
    # server-only
    MISSING_BEFORE = 1 << 8      # gap in sequence numbers
    DRIFT_SUSPECTED = 1 << 9     # disagrees with reference station


@dataclass
class SensorMeta:
    """Description of one physical sensor"""
    device_id: str
    lat: float
    lon: float
    height_m: float
    site_description: str = ""
    installed_at: Optional[datetime] = None


@dataclass
class Uplink:
    """Raw message as received from the network, before decoding."""
    device_id: str
    received_at: datetime
    payload: bytes
    rssi: Optional[float] = None
    snr: Optional[float] = None


@dataclass
class Measurement:
    """One decoded 10-minute window, in physical units."""
    device_id: str
    ts: datetime
    seq: int
    mean_speed_ms: float
    gust_ms: float
    mean_dir_deg: float
    std_speed_ms: float
    temp_c: Optional[float]
    battery_v: float
    flags: QualityFlag = QualityFlag.OK

    @property
    def is_usable(self) -> bool:
        bad = (QualityFlag.OUT_OF_RANGE | QualityFlag.STUCK |
               QualityFlag.SENSOR_FAULT | QualityFlag.DRIFT_SUSPECTED)
        return not (self.flags & bad)
