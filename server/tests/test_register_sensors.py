import importlib.util
from pathlib import Path

import pytest

from uwsn.storage import Repository

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "register_sensors.py"
_spec = importlib.util.spec_from_file_location("register_sensors", _SCRIPT)
reg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reg)

HEADER = "device_id,lat,lon,height_m,site_description,installed_at\n"


def write(tmp_path, text, name="s.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_example_file_is_valid():
    sensors, errors, warnings = reg.read_csv(_SCRIPT.parents[1] / "sensors.example.csv")
    assert not errors and not warnings and len(sensors) == 2


def test_register_then_update(tmp_path):
    db = str(tmp_path / "db.sqlite")
    csv1 = write(tmp_path, HEADER + 'uwsn-01,46.52,6.57,4,"EPFL, BC",2026-12-01\n')
    assert reg.main([str(csv1), "--db", db]) == 0
    csv2 = write(tmp_path, HEADER + "uwsn-01,46.53,6.58,5,moved,\nuwsn-02,46.5,6.6,3,new,\n", "s2.csv")
    assert reg.main([str(csv2), "--db", db]) == 0
    df = Repository(db).load_sensors().set_index("device_id")
    assert len(df) == 2 and df.loc["uwsn-01", "lat"] == 46.53 and df.loc["uwsn-01", "site_description"] == "moved"


def test_semicolons_and_decimal_commas_from_excel(tmp_path):
    p = write(tmp_path, "device_id;lat;lon;height_m;site_description;installed_at\n"
                        "uwsn-01;46,52;6,57;4;Flon;2026-12-01T14:30\n")
    sensors, errors, _ = reg.read_csv(p)
    assert not errors and sensors[0].lat == 46.52 and sensors[0].installed_at.hour == 14


def test_errors_block_everything(tmp_path):
    db = str(tmp_path / "db.sqlite")
    p = write(tmp_path, HEADER + "uwsn-01,46.52,6.57,4,ok,\nUWSN 02,abc,6.57,400,bad,yesterday\n")
    assert reg.main([str(p), "--db", db]) == 1
    assert Repository(db).load_sensors().empty                   # the good row was not written either
    _, errors, _ = reg.read_csv(p)
    text = " ".join(errors)
    assert "line 3" in text and "TTN ID" in text and "not a number" in text
    assert "height_m" in text and "installed_at" in text


def test_duplicate_device_and_missing_column(tmp_path):
    _, errors, _ = reg.read_csv(write(tmp_path, HEADER + "uwsn-01,46.5,6.5,3,,\nuwsn-01,46.5,6.5,3,,\n"))
    assert any("already on line 2" in e for e in errors)
    _, errors, _ = reg.read_csv(write(tmp_path, "device_id,lat\nuwsn-01,46.5\n", "bad.csv"))
    assert any("missing column" in e for e in errors)


def test_swapped_coordinates_warning():
    _, errors, warnings = reg.parse_sensor(dict(device_id="uwsn-01", lat="6.57", lon="46.52", height_m="4"))
    assert not errors and "swapped" in warnings[0]


def test_add_from_command_line(tmp_path, capsys):
    db = str(tmp_path / "db.sqlite")
    assert reg.main(["--add", "uwsn-07", "--lat", "46.5", "--lon", "6.6", "--height", "3",
                     "--db", db, "--list"]) == 0
    assert "uwsn-07" in capsys.readouterr().out
