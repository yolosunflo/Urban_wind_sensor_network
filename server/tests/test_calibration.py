import struct

import numpy as np
import pandas as pd
import pytest

from uwsn.calibration import CMD_SET_CALIB, CalibrationManager


def test_build_downlink_layout():
    raw = CalibrationManager().build_downlink(gain=1.2345, offset_ms=0.25, dir_offset_deg=-12.5,
                                              temp_offset_c=-0.3)
    assert len(raw) == 9
    assert struct.unpack(">BHhhh", raw) == (CMD_SET_CALIB, 12345, 250, -125, -30)


def test_direction_offset_wrapped():
    raw = CalibrationManager().build_downlink(1.0, 0.0, 350.0, 0.0)
    assert struct.unpack(">BHhhh", raw)[3] == -100            # 350 deg = -10 deg


def test_out_of_range_rejected():
    with pytest.raises(ValueError):
        CalibrationManager().build_downlink(0.0, 0.0, 0.0, 0.0)  # zero gain


def test_corrected_params_give_reference_speed():
    rng = np.random.default_rng(0)
    ref = pd.Series(rng.uniform(1, 10, 30))
    f = (ref - 0.3) / 0.9                                       # true law: ref = 0.9 f + 0.3
    old_gain, old_off = 1.0, 0.0
    node = old_gain * f + old_off
    cm = CalibrationManager()
    rep = cm.check_drift("a", node, ref)
    g, o = cm.corrected_speed_params(rep, old_gain, old_off)
    assert g == pytest.approx(0.9) and o == pytest.approx(0.3)


def test_too_few_points():
    with pytest.raises(ValueError):
        CalibrationManager().check_drift("a", pd.Series([1.0, 2.0]), pd.Series([1.1, 2.1]))
