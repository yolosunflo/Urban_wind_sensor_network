"""Big tests: the real node code and the real server code, talking through the payload bytes.

The firmware's Calibration, Aggregator and PayloadCodec are compiled for the computer with
tools/node_sim.cpp (fake sensor values instead of the hardware). Its uplinks are wrapped in
a TTN message and go through the server as if they came from TTN; the server's calibration
downlinks go back into the simulated node.

Needs a C++ compiler (g++ or clang++); the tests are skipped if there is none.
"""
import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from uwsn.analysis import Analyzer
from uwsn.calibration import CalibrationManager
from uwsn.decoder import PayloadDecoder
from uwsn.ingestion import parse_ttn_uplink
from uwsn.models import QualityFlag
from uwsn.pipeline import Pipeline
from uwsn.storage import Repository
from uwsn.validation import DataValidator

FIRMWARE = Path(__file__).resolve().parents[2] / "firmware"
CXX = shutil.which("g++") or shutil.which("clang++") or shutil.which("c++")
T0 = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
STEP = timedelta(minutes=10)

pytestmark = pytest.mark.skipif(CXX is None or not (FIRMWARE / "tools" / "node_sim.cpp").exists(),
                                reason="needs a C++ compiler and the firmware folder")


# ---------------------------------------------------------------- helpers

@pytest.fixture(scope="module")
def node_sim(tmp_path_factory):
    """Compiles the simulator once for all the tests of this file."""
    exe = tmp_path_factory.mktemp("sim") / ("node_sim.exe" if os.name == "nt" else "node_sim")
    sources = [FIRMWARE / "tools" / "node_sim.cpp"] + [
        FIRMWARE / "src" / f for f in ("Aggregator.cpp", "PayloadCodec.cpp", "Calibration.cpp")]
    cmd = [CXX, "-std=c++17", "-O1", "-D_USE_MATH_DEFINES", f"-I{FIRMWARE / 'include'}",
           f"-I{FIRMWARE / 'src'}", *map(str, sources), "-o", str(exe)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, "the firmware does not compile:\n" + res.stderr
    return exe


def run_node(exe, *commands) -> list[str]:
    """Sends commands to a fresh simulated node, returns its output lines."""
    res = subprocess.run([str(exe)], input="\n".join(commands) + "\nquit\n",
                         capture_output=True, text=True, timeout=60, check=True)
    return res.stdout.splitlines()


def uplinks(lines) -> list[bytes]:
    return [bytes.fromhex(l.split()[1]) for l in lines if l.startswith("uplink ")]


def ttn_message(device_id: str, payload: bytes, t: datetime) -> bytes:
    """What TTN would publish on MQTT for this uplink."""
    return json.dumps({
        "end_device_ids": {"device_id": device_id},
        "received_at": t.isoformat().replace("+00:00", "Z"),
        "uplink_message": {"f_port": 1, "frm_payload": base64.b64encode(payload).decode(),
                           "rx_metadata": [{"rssi": -80, "snr": 7.5}]},
    }).encode()


def receive(payloads, device_id="uwsn-01", repo=None) -> Repository:
    """The server side: TTN JSON -> parse -> pipeline -> database. One message every 10 min."""
    repo = repo or Repository(":memory:")
    pipeline = Pipeline(repo, PayloadDecoder(), DataValidator())
    for i, p in enumerate(payloads):
        pipeline.handle_uplink(parse_ttn_uplink(ttn_message(device_id, p, T0 + i * STEP)))
    return repo


# ---------------------------------------------------------------- tests

def test_one_window_from_sensor_values_to_database(node_sim):
    # default calibration: 1 m/s per Hz, so 3 pulses per second = 3 m/s
    df = receive(uplinks(run_node(node_sim, "window 3 90 15"))).load_measurements()
    assert len(df) == 1
    m = df.iloc[0]
    assert m["mean_speed_ms"] == pytest.approx(3.0, abs=0.01)
    assert m["mean_dir_deg"] == pytest.approx(90.0, abs=1.0)
    assert m["temp_c"] == pytest.approx(15.0, abs=0.01)
    assert m["battery_v"] == pytest.approx(3.6, abs=0.01)
    assert m["flags"] == 0 and m["seq"] == 0


def test_fractional_pulse_rate_and_wind_from_north(node_sim):
    df = receive(uplinks(run_node(node_sim, "window 0.5 359 15"))).load_measurements()
    m = df.iloc[0]
    assert m["mean_speed_ms"] == pytest.approx(0.5, abs=0.01)       # one pulse every 2 s
    assert min(m["mean_dir_deg"], 360 - m["mean_dir_deg"]) < 1.5    # around north, not 180


def test_a_day_of_windows_to_hourly_analysis(node_sim):
    speeds = [1, 2, 3, 4, 5, 6] * 4                                  # 4 hours
    lines = run_node(node_sim, *[f"window {s} 200 10" for s in speeds])
    df = receive(uplinks(lines)).load_measurements()
    assert len(df) == len(speeds) and df["seq"].tolist() == list(range(len(speeds)))
    hourly = Analyzer(df).hourly()
    assert len(hourly) == 4
    assert np.allclose(hourly["mean_speed_ms"], 3.5, atol=0.01)
    assert np.allclose(hourly["mean_dir_deg"], 200, atol=1.0)


def test_broken_sensors_are_flagged_and_left_out(node_sim):
    lines = run_node(node_sim,
                     "window 3 90 15",          # fine
                     "window 3 90 15 1",        # anemometer never answers
                     "window 3 90 none")        # temperature sensor never answers
    df = receive(uplinks(lines)).load_measurements()
    flags = df["flags"].tolist()
    assert flags[0] == 0
    assert flags[1] & QualityFlag.SENSOR_FAULT
    assert flags[2] & QualityFlag.TEMP_FAULT and not flags[2] & QualityFlag.SENSOR_FAULT
    assert pd.isna(df["temp_c"].iloc[2])
    repo = receive(uplinks(lines))
    assert len(repo.load_measurements(usable_only=True)) == 2      # the faulty window is excluded


def test_calibration_downlink_changes_the_next_measurements(node_sim):
    cmd = CalibrationManager().build_downlink(gain=0.5, offset_ms=0.2, dir_offset_deg=10.0,
                                              temp_offset_c=-1.0)
    lines = run_node(node_sim,
                     "window 4 90 15",           # before: 4 m/s
                     f"calib {cmd.hex()}",
                     "window 4 90 15",           # after: 0.5 * 4 + 0.2 = 2.2 m/s
                     "reset",                    # reboot: the calibration must come back from flash
                     "window 4 90 15")
    assert "calib ok" in lines
    df = receive(uplinks(lines)).load_measurements()
    assert df["mean_speed_ms"].tolist() == pytest.approx([4.0, 2.2, 2.2], abs=0.01)
    assert df["mean_dir_deg"].tolist() == pytest.approx([90.0, 100.0, 100.0], abs=1.0)
    assert df["temp_c"].tolist() == pytest.approx([15.0, 14.0, 14.0], abs=0.01)


def test_reset_downlink_and_garbage_downlink(node_sim):
    cm = CalibrationManager()
    lines = run_node(node_sim,
                     f"calib {cm.build_downlink(2.0, 0, 0, 0).hex()}",
                     "calib 7f0000",                             # unknown command
                     "window 1 0 10",                            # still gain 2 -> 2 m/s
                     f"calib {cm.build_reset_downlink().hex()}",
                     "window 1 0 10")                            # defaults -> 1 m/s
    assert lines.count("calib rejected") == 1
    speeds = receive(uplinks(lines)).load_measurements()["mean_speed_ms"].tolist()
    assert speeds == pytest.approx([2.0, 1.0], abs=0.01)


def test_full_calibration_workflow(node_sim):
    """Bench: the node runs next to a reference, the server fits, sends, and the node is right."""
    true_gain, true_offset = 0.9, 0.3                  # the real law of our cups (unknown to the node)
    freqs = [1, 2, 3, 4, 5, 6, 7, 8]
    reference = pd.Series([true_gain * f + true_offset for f in freqs])

    before = receive(uplinks(run_node(node_sim, *[f"window {f} 0 10" for f in freqs])))
    node = before.load_measurements()["mean_speed_ms"].reset_index(drop=True)

    cm = CalibrationManager()
    report = cm.check_drift("uwsn-01", node, reference)
    assert report.needs_recalibration
    gain, offset = cm.corrected_speed_params(report, old_gain=1.0, old_offset_ms=0.0)

    lines = run_node(node_sim, f"calib {cm.build_downlink(gain, offset, 0, 0).hex()}",
                     *[f"window {f} 0 10" for f in freqs])
    after = receive(uplinks(lines)).load_measurements()["mean_speed_ms"].reset_index(drop=True)
    assert np.allclose(after, reference, atol=0.02)
    assert not cm.check_drift("uwsn-01", after, reference).needs_recalibration
