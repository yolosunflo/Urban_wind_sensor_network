from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from uwsn.dashboard import data
from uwsn.models import QualityFlag

T0 = pd.Timestamp("2026-11-01", tz="UTC")
NOW = datetime(2026, 11, 2, tzinfo=timezone.utc)


def frame(rows):
    """rows: (device, minutes, speed, flags, temp)"""
    return pd.DataFrame([dict(device_id=d, ts=T0 + pd.Timedelta(minutes=m), seq=0, mean_speed_ms=s,
                              gust_ms=s + 1, mean_dir_deg=90.0, std_speed_ms=0.3, temp_c=t,
                              battery_v=3.9, flags=f) for d, m, s, f, t in rows])


def test_flag_text():
    assert data.flag_text(0) == "OK"
    assert data.flag_text(int(QualityFlag.SPIKE | QualityFlag.LOW_BATTERY)) == "Spike, Low battery"


def test_insert_gaps_breaks_line_only_where_packets_are_missing():
    df = frame([("a", 0, 1, 0, 5), ("a", 10, 1, 0, 5), ("a", 50, 1, 0, 5)])
    out = data.insert_gaps(df[["device_id", "ts", "mean_speed_ms"]])
    assert len(out) == 4
    assert out["mean_speed_ms"].isna().sum() == 1
    assert out.loc[out["mean_speed_ms"].isna(), "ts"].iloc[0] == T0 + pd.Timedelta(minutes=20)


def test_series_frames_modes():
    df = frame([("a", 0, 1, 0, 5), ("a", 10, 30, int(QualityFlag.SPIKE), 5),
                ("a", 20, 1, int(QualityFlag.TEMP_FAULT), 85.0)])
    for mode, n_flagged_wind in [("hide", 0), ("grey", 1), ("show", 0)]:
        lines, flagged = data.series_frames(df, mode)
        assert len(flagged["mean_speed_ms"]) == n_flagged_wind
    lines, _ = data.series_frames(df, "hide")
    assert lines["mean_speed_ms"].isna().tolist() == [False, True, False]     # spike hidden
    assert lines["temp_c"].isna().tolist() == [False, False, True]            # bad temperature hidden
    lines, _ = data.series_frames(df, "show")
    assert lines["mean_speed_ms"].max() == 30                                 # nothing hidden
    _, flagged = data.series_frames(df, "grey")
    assert flagged["temp_c"]["temp_c"].tolist() == [85.0]


def sensors_table():
    return pd.DataFrame([
        dict(device_id="on", lat=47.0, lon=8.0, height_m=3, site_description="Main street, canyon",
             installed_at=(NOW - timedelta(days=30)).isoformat()),
        dict(device_id="old", lat=47.0, lon=8.0, height_m=3, site_description="",
             installed_at=(NOW - timedelta(days=200)).isoformat()),
        dict(device_id="soon", lat=47.0, lon=8.0, height_m=3, site_description="",
             installed_at=(NOW - timedelta(days=170)).isoformat())])


def test_network_health_states():
    t_on = NOW - timedelta(minutes=10)
    rows = pd.DataFrame([
        dict(device_id="on", ts=t_on, battery_v=3.9, flags=0),
        dict(device_id="old", ts=t_on, battery_v=3.2, flags=int(QualityFlag.LOW_BATTERY)),
        dict(device_id="soon", ts=NOW - timedelta(days=2), battery_v=3.8, flags=0)])
    avail = pd.Series({"on": 1.0, "old": 0.9, "soon": 0.5})
    h = data.network_health(rows, sensors_table(), ["on", "old", "soon", "ghost"], avail, now=NOW)
    h = h.set_index("device_id")
    assert h.loc["on", "status"] == "Online" and h.loc["soon", "status"] == "Offline"
    assert h.loc["ghost", "status"] == "No data"
    assert h.loc["old", "low_battery"] and not h.loc["on", "low_battery"]
    assert h.loc["old", "calibration"] == "Due" and h.loc["old", "calibration_due"]
    assert h.loc["soon", "calibration"] == "Due in 10 d" and not h.loc["soon", "calibration_due"]
    assert h.loc["on", "calibration"] == "OK"
    items = data.attention_items(h.reset_index())
    assert any("offline" in i for i in items) and any("battery" in i for i in items)


def test_sensor_summary_and_missing_sensor_metadata():
    df = frame([("a", m, 0.5 if m < 20 else 3.0, 0, 10.0) for m in range(0, 40, 10)])
    s = data.sensor_summary(df, df, pd.DataFrame(), ["a"], low_wind_ms=1.0)
    assert s.loc["a", "low_wind"] == 0.5 and s.loc["a", "mean_speed"] == 1.75
    assert np.isnan(s.loc["a", "lat"])                      # no sensors table: still works
    empty = data.sensor_summary(df.iloc[0:0], df, pd.DataFrame(), ["a"], 1.0)
    assert np.isnan(empty.loc["a", "mean_speed"])


def test_export_frame():
    out = data.export_frame(frame([("a", 0, 1, int(QualityFlag.STUCK), 5)]))
    assert not out.loc[0, "usable"] and out.loc[0, "flags_text"] == "Stuck"
    assert isinstance(out.loc[0, "ts"], str)


def hourly_frame():
    ts = pd.date_range("2026-11-01 00:00", periods=48, freq="1h", tz="UTC")       # 2 days
    rows = [dict(device_id=d, ts=t, mean_speed_ms=(2.0 if d == "a" else 4.0) + (t.hour == 12),
                 gust_ms=5.0, mean_dir_deg=90.0, temp_c=5.0) for d in ("a", "b") for t in ts]
    return pd.DataFrame(rows)


def test_daily_cycle_uses_local_hours():
    c = data.daily_cycle(hourly_frame())
    a = c[c["device_id"] == "a"].set_index("hour")["mean_speed_ms"]
    assert len(a) == 24 and a.idxmax() == 13               # 12:00 UTC = 13:00 in Switzerland in winter
    assert a.max() == 3.0 and a.min() == 2.0


def test_daily_mean_adds_network_row():
    d = data.daily_mean(hourly_frame())
    assert set(d["device_id"]) == {"a", "b", "Network"}
    net = d[d["device_id"] == "Network"]
    assert len(net) >= 2 and net["mean_speed_ms"].between(3.0, 3.2).all()


def test_hour_by_day_shape_and_gaps():
    h = hourly_frame()
    g = data.hour_by_day(h)
    assert list(g.index) == list(range(24)) and g.shape[1] >= 2
    assert data.hour_by_day(h.iloc[0:0]).shape[0] == 24


def test_map_steps_vector_direction_and_step_size():
    h = hourly_frame()
    h.loc[h["device_id"] == "b", "mean_dir_deg"] = 350.0
    h.loc[(h["device_id"] == "b") & (h["ts"].dt.hour % 2 == 1), "mean_dir_deg"] = 10.0
    steps, step = data.map_steps(h, max_steps=300)
    assert step == 1 and len(steps) == 96
    steps, step = data.map_steps(h, max_steps=20)                         # 48 h / 3 h = 16 steps
    assert step == 3 and steps["step_ts"].nunique() == 16
    b = steps[steps["device_id"] == "b"]["direction"]
    assert (np.minimum(b, 360 - b) < 20).all()                            # around north, not 180
    assert data.map_steps(h.iloc[0:0])[0].empty
