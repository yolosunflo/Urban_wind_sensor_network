from datetime import datetime, timedelta, timezone
from uwsn.models import Measurement, QualityFlag, SensorMeta
from uwsn.storage import Repository

T0 = datetime(2026, 11, 1, tzinfo=timezone.utc)


def meas(device, minutes, flags=QualityFlag.OK):
    return Measurement(device, T0 + timedelta(minutes=minutes), minutes // 10, 3.0, 4.0,
                       180.0, 0.5, 10.0, 3.9, flags)


def repo_with_data():
    repo = Repository(":memory:")
    for dev in ("a", "b"):
        for i in range(0, 60 * 48, 10):                       # two days of 10-min windows
            repo.save_measurement(meas(dev, i, QualityFlag.SPIKE if i == 100 else QualityFlag.OK))
    return repo


def test_no_filter_returns_everything():
    assert len(repo_with_data().load_measurements()) == 2 * 288


def test_filter_by_sensor():
    df = repo_with_data().load_measurements(device_ids=["b"])
    assert set(df["device_id"]) == {"b"}


def test_empty_sensor_list_returns_nothing():
    assert repo_with_data().load_measurements(device_ids=[]).empty


def test_date_range_start_inclusive_end_exclusive():
    df = repo_with_data().load_measurements(start="2026-11-02", end="2026-11-03")
    assert df["ts"].min() == datetime(2026, 11, 2, tzinfo=timezone.utc)
    assert df["ts"].max() == datetime(2026, 11, 2, 23, 50, tzinfo=timezone.utc)
    assert len(df) == 2 * 144


def test_date_range_accepts_datetime_objects():
    df = repo_with_data().load_measurements(start=T0 + timedelta(hours=1),
                                            end=T0 + timedelta(hours=2))
    assert len(df) == 2 * 6


def test_usable_only_drops_unreliable_rows():
    repo = repo_with_data()
    assert len(repo.load_measurements(usable_only=True)) == 2 * 288 - 2


def test_low_battery_does_not_make_a_row_unusable():
    repo = Repository(":memory:")
    repo.save_measurement(meas("a", 0, QualityFlag.LOW_BATTERY | QualityFlag.CALIBRATION_DUE))
    assert len(repo.load_measurements(usable_only=True)) == 1


def test_save_sensor_inserts_and_updates():
    repo = Repository(":memory:")
    repo.save_sensor(SensorMeta("a", 47.37, 8.54, 3.0, "Main street", T0))
    repo.save_sensor(SensorMeta("a", 47.38, 8.55, 3.0))
    sensors = repo.load_sensors()
    assert len(sensors) == 1 and sensors.loc[0, "lat"] == 47.38
