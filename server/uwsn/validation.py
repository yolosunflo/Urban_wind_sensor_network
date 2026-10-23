"""Data quality control. Never delete data: only add flags, so the raw record stays."""
from collections import defaultdict, deque
from .config import SETTINGS as S
from .models import Measurement, QualityFlag


class DataValidator:
    def __init__(self):
        self._history = defaultdict(lambda: deque(maxlen=S.stuck_windows))
        self._last_seq = {}

    def validate(self, m: Measurement) -> Measurement:
        flags = m.flags

        # 1. physical plausibility
        if not (0 <= m.mean_speed_ms <= S.max_speed_ms) or m.gust_ms < m.mean_speed_ms:
            flags |= QualityFlag.OUT_OF_RANGE
        if not (0 <= m.mean_dir_deg < 360):
            flags |= QualityFlag.OUT_OF_RANGE

        # 2. spike vs previous window
        hist = self._history[m.device_id]
        if hist and abs(m.mean_speed_ms - hist[-1]) > S.max_jump_ms:
            flags |= QualityFlag.SPIKE

        # 3. stuck sensor: N identical consecutive means (and not all ~0)
        hist.append(m.mean_speed_ms)
        if len(hist) == hist.maxlen and len(set(hist)) == 1 and hist[0] > 0.0:
            flags |= QualityFlag.STUCK

        # 4. missing packets (sequence gap, handle 16-bit wrap-around)
        last = self._last_seq.get(m.device_id)
        if last is not None and ((m.seq - last) % 65536) > 1:
            flags |= QualityFlag.MISSING_BEFORE
        self._last_seq[m.device_id] = m.seq

        # 5. battery
        if m.battery_v < S.low_battery_v:
            flags |= QualityFlag.LOW_BATTERY

        m.flags = flags
        return m
