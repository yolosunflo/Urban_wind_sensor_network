"""TTN message format, without a broker: what TTN sends us and what we send to TTN."""
import base64
import json
from datetime import datetime, timedelta, timezone

from uwsn.ingestion import _parse_time, parse_ttn_uplink, ttn_downlink_message


def ttn_message(payload: bytes = b"\x01\x02", **extra) -> bytes:
    """A TTN v3 uplink message, reduced to the fields we use."""
    msg = {
        "end_device_ids": {"device_id": "uwsn-01", "application_ids": {"application_id": "uwsn"}},
        "received_at": "2026-11-16T12:00:23.123456789Z",
        "uplink_message": {
            "f_port": 1,
            "frm_payload": base64.b64encode(payload).decode(),
            "rx_metadata": [{"gateway_ids": {"gateway_id": "g1"}, "rssi": -87, "snr": 6.25}],
        },
    }
    msg.update(extra)
    return json.dumps(msg).encode()


def test_parse_uplink_fields():
    up = parse_ttn_uplink(ttn_message(b"\x01\x02\x03"))
    assert up.device_id == "uwsn-01"
    assert up.payload == b"\x01\x02\x03"
    assert up.rssi == -87 and up.snr == 6.25
    assert up.received_at == datetime(2026, 11, 16, 12, 0, 23, 123456, tzinfo=timezone.utc)


def test_message_without_application_data_is_ignored():
    raw = json.loads(ttn_message())
    del raw["uplink_message"]["frm_payload"]           # e.g. a MAC-only frame
    assert parse_ttn_uplink(json.dumps(raw).encode()) is None


def test_missing_radio_metadata_is_fine():
    raw = json.loads(ttn_message())
    del raw["uplink_message"]["rx_metadata"]
    up = parse_ttn_uplink(json.dumps(raw).encode())
    assert up.rssi is None and up.snr is None


def test_time_with_nanoseconds_and_without_fraction():
    assert _parse_time("2026-11-16T12:00:23.5Z").microsecond == 500000
    assert _parse_time("2026-11-16T12:00:23Z") == datetime(2026, 11, 16, 12, 0, 23, tzinfo=timezone.utc)


def test_missing_time_uses_now():
    assert abs(_parse_time(None) - datetime.now(timezone.utc)) < timedelta(seconds=5)


def test_downlink_message_for_ttn():
    msg = json.loads(ttn_downlink_message(b"\x02"))
    down = msg["downlinks"][0]
    assert down["f_port"] == 2
    assert base64.b64decode(down["frm_payload"]) == b"\x02"
