import numpy as np
import pandas as pd
import pytest
from uwsn.analysis import Analyzer, vector_mean_direction

T0 = pd.Timestamp("2026-11-01", tz="UTC")


def frame(rows):
    """rows: (device, minutes, speed, direction, flags)"""
    return pd.DataFrame([dict(device_id=d, ts=T0 + pd.Timedelta(minutes=m), mean_speed_ms=s,
                              gust_ms=s + 1, mean_dir_deg=dr, temp_c=10.0, flags=f)
                         for d, m, s, dr, f in rows])


def test_vector_mean_wraps_around_north():
    mean = vector_mean_direction(pd.Series([2.0, 2.0]), pd.Series([359.0, 1.0]))
    assert min(mean, 360 - mean) < 0.01          # 0 degrees, not 180


def test_vector_mean_is_speed_weighted():
    mean = vector_mean_direction(pd.Series([9.0, 1.0]), pd.Series([0.0, 90.0]))
    assert 0 < mean < 10                         # the strong wind dominates


def test_vector_mean_opposite_winds_cancel_out():
    assert np.isnan(vector_mean_direction(pd.Series([2.0, 2.0]), pd.Series([0.0, 180.0])))


def test_hourly_uses_vector_average_and_skips_unusable():
    df = frame([("a", 0, 2.0, 350.0, 0), ("a", 10, 2.0, 10.0, 0), ("a", 20, 30.0, 180.0, 4)])
    h = Analyzer(df).hourly()
    assert len(h) == 1
    assert h.loc[0, "mean_speed_ms"] == 2.0                      # spike excluded
    assert min(h.loc[0, "mean_dir_deg"], 360 - h.loc[0, "mean_dir_deg"]) < 0.01


def test_hourly_keeps_gap_hours_as_nan():
    df = frame([("a", 0, 2.0, 90.0, 0), ("a", 180, 2.0, 90.0, 0)])
    h = Analyzer(df).hourly()
    assert len(h) == 4 and h["mean_speed_ms"].isna().sum() == 2


def test_hourly_empty():
    assert Analyzer(frame([("a", 0, 2.0, 90.0, 4)])).hourly().empty


def test_wind_rose_sums_to_100_and_has_every_cell():
    rng = np.random.default_rng(0)
    df = frame([("a", i * 10, rng.uniform(0, 9), rng.uniform(0, 360), 0) for i in range(200)])
    rose = Analyzer(df).wind_rose("a", n_sectors=8)
    assert len(rose) == 8 * 5
    assert rose["frequency"].sum() == pytest.approx(100)


def test_wind_rose_sectors_are_centred_on_compass_points():
    df = frame([("a", 0, 3.0, 359.0, 0), ("a", 10, 3.0, 5.0, 0), ("a", 20, 3.0, 95.0, 0)])
    rose = Analyzer(df).wind_rose("a", n_sectors=16)
    hit = rose[rose["count"] > 0].groupby("sector_deg")["count"].sum()
    assert hit.to_dict() == {0.0: 2, 90.0: 1}


def test_wind_rose_ignores_other_sensors_and_unusable():
    df = frame([("a", 0, 3.0, 90.0, 0), ("a", 10, 3.0, 180.0, 1), ("b", 0, 3.0, 270.0, 0)])
    rose = Analyzer(df).wind_rose("a")
    assert rose["count"].sum() == 1


def test_wind_rose_no_data():
    rose = Analyzer(frame([("a", 0, 3.0, 90.0, 0)])).wind_rose("zzz")
    assert rose["count"].sum() == 0 and rose["frequency"].sum() == 0


def test_availability():
    rows = [("a", m, 2.0, 0.0, 0) for m in range(0, 100, 10)]                    # 10 of 10
    rows += [("b", m, 2.0, 0.0, 0) for m in range(0, 100, 20)]                   # 5 of 10
    rows += [("c", m, 2.0, 0.0, 0) for m in range(0, 40, 10)]                    # stopped: 4 of 10
    av = Analyzer(frame(rows)).availability()
    assert av["a"] == 1.0 and av["b"] == 0.5 and av["c"] == 0.4


def test_availability_counts_flagged_rows():
    df = frame([("a", 0, 2.0, 0.0, 4), ("a", 10, 2.0, 0.0, 1)])
    assert Analyzer(df).availability()["a"] == 1.0


def test_wind_rose_speed_class_is_always_ordered_categorical():
    for rows in ([("a", 0, 3.0, 90.0, 0)], [("a", 0, 3.0, 90.0, 0), ("a", 10, 0.2, 10.0, 0)]):
        cls = Analyzer(frame(rows)).wind_rose("a")["speed_class"]
        assert cls.cat.ordered and list(cls.cat.categories)[0] == "0-1 m/s"
