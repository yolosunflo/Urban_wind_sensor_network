import struct
from datetime import datetime, timezone
from uwsn.decoder import PayloadDecoder
from uwsn.models import Uplink


def test_roundtrip_known_payload():
    # 1.50 m/s mean, 3.20 gust, 270.0 deg, std 0.5, temp n/a, 3.90 V, flags 0
    raw = struct.pack(">BHHHHBhBB", 1, 42, 150, 320, 2700, 10, -32768, 190, 0)
    m = PayloadDecoder().decode(Uplink("node-01", datetime.now(timezone.utc), raw))
    assert abs(m.mean_speed_ms - 1.5) < 1e-9
    assert m.temp_c is None
    assert abs(m.battery_v - 3.9) < 1e-9


def test_temperature_decoded():
    # 0.80 m/s mean, 1.50 gust, 90.0 deg, std 0.2, temp 21.50 C, 3.90 V, flags 0
    raw = struct.pack(">BHHHHBhBB", 1, 43, 80, 150, 900, 4, 2150, 190, 0)
    m = PayloadDecoder().decode(Uplink("node-01", datetime.now(timezone.utc), raw))
    assert abs(m.temp_c - 21.5) < 1e-9
