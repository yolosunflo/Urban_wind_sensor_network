"""Data quality control. Never delete data: only add flags, so the raw record stays."""
from collections import defaultdict, deque
from .config import SETTINGS as S
from .models import Measurement, QualityFlag


class DataValidator:
    """
    Remembers the recent history per sensor
    """
    def __init__(self):
        self._history = defaultdict(lambda: deque(maxlen=S.stuck_windows))
        self._last_seq = {}
        self._last_temp = {}

    def validate(self, m: Measurement) -> Measurement:
        """
        Adds flags to track validity of the data
        """
        flags = m.flags

        # Spike vs previous window
        hist = self._history[m.device_id]
        is_spike = bool(hist) and abs(m.mean_speed_ms - hist[-1]) > S.max_jump_ms
        if is_spike:
            flags |= QualityFlag.SPIKE
        else:
            hist.append(m.mean_speed_ms)          # only normal values go into the history
            if len(hist) == hist.maxlen and len(set(hist)) == 1 and hist[0] > 0.0:
                flags |= QualityFlag.STUCK

        # Stuck sensor: N identical consecutive means (and not all ~0)
        hist.append(m.mean_speed_ms)
        if len(hist) == hist.maxlen and len(set(hist)) == 1 and hist[0] > 0.0:
            flags |= QualityFlag.STUCK

        # Missing packets
        last = self._last_seq.get(m.device_id)
        if last is not None and ((m.seq - last) % 65536) > 1:
            flags |= QualityFlag.MISSING_BEFORE
        self._last_seq[m.device_id] = m.seq

        # Temperature: only flags the temperature, wind data stays usable
        if m.temp_c is None or not (S.temp_min_c <= m.temp_c <= S.temp_max_c):
            flags |= QualityFlag.TEMP_FAULT
        else:
            prev = self._last_temp.get(m.device_id)
            if not (prev is not None and abs(m.temp_c - prev) > S.max_temp_jump_c):
                flags |= QualityFlag.TEMP_FAULT
            self._last_temp[m.device_id] = m.temp_c

        m.flags = flags
        return m
