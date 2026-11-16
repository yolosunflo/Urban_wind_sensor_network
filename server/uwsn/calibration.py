"""Server-side calibration: checks a node against a reference and sends it new calibration values.

The node has no clock, so it never decides by itself that it needs calibrating. The server
decides, and sends the new values in a downlink (format: docs/payload_format.md, port 2).
The node applies them as soon as it receives them and keeps them in flash, so they survive
a reset or a battery change.

Prototype workflow:
    1. Run the node next to a reference (fan bench + reference anemometer).
    2. check_drift(): compare node and reference speeds taken at the same moments.
    3. corrected_speed_params(): new gain and offset computed from that comparison.
    4. build_downlink() then ingestion.send_downlink(): the node receives the values just
       after its next uplink (LoRaWAN class A), so up to one window (10 min) later.
"""
import struct
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SETTINGS as S

CMD_SET_CALIB = 0x01      # 9 bytes: command + gain + speed offset + direction offset + temperature offset
CMD_RESET_CALIB = 0x02    # 1 byte: back to the firmware defaults
_SET_FMT = ">BHhhh"       # big-endian, see docs/payload_format.md
MIN_POINTS = 5            # fewer paired points than this: no fit


@dataclass
class DriftReport:
    device_id: str
    gain_ratio: float      # slope of node vs reference (1.0 = perfect)
    offset_ms: float       # intercept (should be ~0)
    r2: float
    needs_recalibration: bool


class CalibrationManager:
    def __init__(self, max_gain_error: float = 0.1, max_offset_ms: float = 0.3):
        self.max_gain_error = max_gain_error
        self.max_offset_ms = max_offset_ms

    def check_drift(self, device_id: str, node: pd.Series, reference: pd.Series) -> DriftReport:
        """
        node / reference: mean speed series (m/s) on the same timestamps.
        Fits node = slope * reference + intercept.
        Raises ValueError if there are too few points, or all at the same speed, to fit a line.
        """
        df = pd.concat([node, reference], axis=1, keys=["n", "r"]).dropna()
        if len(df) < MIN_POINTS or df["r"].nunique() < 2:
            raise ValueError(f"{device_id}: {len(df)} paired points, need at least {MIN_POINTS} "
                             "at different reference speeds to fit a line")
        slope, intercept = np.polyfit(df["r"], df["n"], 1)
        r2 = float(np.corrcoef(df["r"], df["n"])[0, 1] ** 2)
        bad = abs(slope - 1) > self.max_gain_error or abs(intercept) > self.max_offset_ms
        return DriftReport(device_id, float(slope), float(intercept), r2, bool(bad))

    @staticmethod
    def corrected_speed_params(report: DriftReport, old_gain: float, old_offset_ms: float):
        """New (gain, offset_ms) for the node, from a drift report made with its old parameters.

        The node computes speed = gain * f + offset and we measured node = slope * ref + intercept,
        so the reference speed is ref = (gain * f + offset - intercept) / slope."""
        return old_gain / report.gain_ratio, (old_offset_ms - report.offset_ms) / report.gain_ratio

    def build_downlink(self, gain: float, offset_ms: float, dir_offset_deg: float,
                       temp_offset_c: float) -> bytes:
        """Encode a 'set calibration' command (9 bytes, see docs/payload_format.md).

        The node REPLACES all four values, so always send the current direction and
        temperature offsets too, even if only the speed changed.
        Raises ValueError if a value does not fit in the format."""
        dir_offset_deg = (dir_offset_deg + 180.0) % 360.0 - 180.0      # same angle, in [-180, 180)
        g = round(gain / S.calib_gain_lsb)
        o = round(offset_ms / S.calib_offset_lsb_ms)
        d = round(dir_offset_deg / S.calib_dir_lsb_deg)
        t = round(temp_offset_c / S.calib_temp_lsb_c)
        if not 0 < g <= 0xFFFF:
            raise ValueError(f"gain {gain} out of range (0, {0xFFFF * S.calib_gain_lsb:.4f}]")
        for name, v in (("speed offset", o), ("direction offset", d), ("temperature offset", t)):
            if not -32768 <= v <= 32767:
                raise ValueError(f"{name} out of range")
        return struct.pack(_SET_FMT, CMD_SET_CALIB, g, o, d, t)

    @staticmethod
    def build_reset_downlink() -> bytes:
        """Command that puts the node back on its default calibration."""
        return bytes([CMD_RESET_CALIB])
