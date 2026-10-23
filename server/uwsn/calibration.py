"""Server-side calibration monitoring: detects drift against a reference sensor
and decides when a node needs recalibration (a downlink can then update it)."""
from dataclasses import dataclass
import numpy as np
import pandas as pd


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
        """node / reference: mean speed series on the same timestamps (e.g. MeteoSwiss or a
        co-located reference anemometer)."""
        df = pd.concat([node, reference], axis=1, keys=["n", "r"]).dropna()
        slope, intercept = np.polyfit(df["r"], df["n"], 1)      # TODO: handle too few points
        r2 = float(np.corrcoef(df["r"], df["n"])[0, 1] ** 2)
        bad = abs(slope - 1) > self.max_gain_error or abs(intercept) > self.max_offset_ms
        return DriftReport(device_id, float(slope), float(intercept), r2, bool(bad))

    def build_downlink(self, device_id: str, new_gain: float, new_offset_v: float) -> bytes:
        """TODO: encode a calibration command for the node (see docs/payload_format.md)."""
        raise NotImplementedError
