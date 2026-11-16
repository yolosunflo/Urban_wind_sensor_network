"""The receive chain without TTN: Uplink -> decode -> validate -> database."""
import struct
from datetime import datetime, timedelta, timezone

from uwsn.decoder import PayloadDecoder
from uwsn.models import QualityFlag, Uplink
from uwsn.pipeline import Pipeline
from uwsn.storage import Repository
from uwsn.validation import DataValidator

T0 = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def payload(seq=1, speed=150, temp=2150, flags=0, version=1) -> bytes:
    # 1.50 m/s mean, 3.20 gust, 270.0 deg, std 0.5, 21.50 C, 3.90 V
    return struct.pack(">BHHHHBhBB", version, seq, speed, 320, 2700, 10, temp, 190, flags)


def make_pipeline():
    repo = Repository(":memory:")
    return repo, Pipeline(repo, PayloadDecoder(), DataValidator())


def count_uplinks(repo) -> int:
    return repo._db.execute("SELECT COUNT(*) FROM uplinks").fetchone()[0]


def test_good_uplink_is_stored_in_both_tables():
    repo, p = make_pipeline()
    p.handle_uplink(Uplink("uwsn-01", T0, payload(), rssi=-90, snr=5))
    df = repo.load_measurements()
    assert count_uplinks(repo) == 1 and len(df) == 1
    row = df.iloc[0]
    assert row["mean_speed_ms"] == 1.5 and row["temp_c"] == 21.5 and row["flags"] == 0


def test_broken_payloads_are_kept_raw_but_not_decoded():
    repo, p = make_pipeline()
    p.handle_uplink(Uplink("uwsn-01", T0, b"\x01\x02"))                         # too short
    p.handle_uplink(Uplink("uwsn-01", T0 + timedelta(minutes=10), payload(version=9)))  # unknown version
    assert count_uplinks(repo) == 2
    assert repo.load_measurements().empty


def test_same_message_twice_gives_one_measurement():
    repo, p = make_pipeline()
    up = Uplink("uwsn-01", T0, payload())
    p.handle_uplink(up)
    p.handle_uplink(up)
    assert count_uplinks(repo) == 2                  # raw log keeps everything
    assert len(repo.load_measurements()) == 1


def test_lost_packet_is_flagged():
    repo, p = make_pipeline()
    p.handle_uplink(Uplink("uwsn-01", T0, payload(seq=1)))
    p.handle_uplink(Uplink("uwsn-01", T0 + timedelta(minutes=30), payload(seq=4)))   # 2 and 3 lost
    flags = repo.load_measurements()["flags"].tolist()
    assert not flags[0] & QualityFlag.MISSING_BEFORE
    assert flags[1] & QualityFlag.MISSING_BEFORE


def test_node_flags_are_kept():
    repo, p = make_pipeline()
    p.handle_uplink(Uplink("uwsn-01", T0, payload(flags=int(QualityFlag.SENSOR_FAULT))))
    assert repo.load_measurements(usable_only=True).empty           # sensor fault: wind unusable
    assert len(repo.load_measurements()) == 1                        # but the row is still there
