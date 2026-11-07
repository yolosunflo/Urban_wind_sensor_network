from datetime import datetime, timezone
from uwsn.models import Measurement, QualityFlag
from uwsn.validation import DataValidator


def make(seq, temp, speed=1.0):
    return Measurement("node-01", datetime.now(timezone.utc), seq, speed, speed + 1,
                       180.0, 0.3, temp, 3.9)


def test_implausible_temperature_flags_temp_only():
    m = DataValidator().validate(make(1, 85.0))
    assert m.flags & QualityFlag.TEMP_FAULT
    assert m.is_usable and not m.has_valid_temp      # wind data still usable


def test_temperature_jump_flagged():
    v = DataValidator()
    v.validate(make(1, 20.0))
    m = v.validate(make(2, 30.0))
    assert m.flags & QualityFlag.TEMP_FAULT


def test_missing_temperature_flagged():
    m = DataValidator().validate(make(1, None))
    assert m.flags & QualityFlag.TEMP_FAULT
