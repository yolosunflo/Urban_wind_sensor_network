"""Register the sensors (where they are) in the database, so the dashboard can show them on the map.

    cd server
    python scripts/register_sensors.py sensors.csv           # add / update every sensor of the file
    python scripts/register_sensors.py --list                # show what is registered
    python scripts/register_sensors.py --add uwsn-01 --lat 46.5191 --lon 6.5668 --height 4 \
        --site "EPFL, BC building" --installed 2026-12-01    # one sensor from the command line

The device_id MUST be the "End device ID" of the node in the TTN console: that is the name
the measurements arrive with. Registering an existing device_id again updates it.
Nothing is written if one row of the file is wrong: fix the file and run it again.

CSV columns (comma or semicolon, first line = header; see sensors.example.csv):
    device_id, lat, lon, height_m, site_description, installed_at
installed_at is a date (2026-12-01) or date and time (2026-12-01T14:30), UTC; it can be empty.
"""
import argparse
import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # so "import uwsn" works

from uwsn.config import SETTINGS                                   # noqa: E402
from uwsn.models import SensorMeta                                 # noqa: E402
from uwsn.storage import Repository                                # noqa: E402

COLUMNS = ["device_id", "lat", "lon", "height_m", "site_description", "installed_at"]
TTN_ID = re.compile(r"^[a-z0-9](?:-?[a-z0-9]){2,35}$")            # TTN rule for device IDs
SWITZERLAND = (45.8, 47.9, 5.9, 10.6)                              # lat min, lat max, lon min, lon max
MAX_HEIGHT_M = 50.0


def parse_sensor(row: dict) -> tuple[Optional[SensorMeta], list[str], list[str]]:
    """One CSV row -> (SensorMeta or None, errors, warnings). Never raises."""
    errors, warnings = [], []
    dev = (row.get("device_id") or "").strip()
    if not dev:
        errors.append("device_id is empty")
    elif not TTN_ID.match(dev):
        errors.append(f"device_id '{dev}' is not a valid TTN ID (lowercase letters, digits and "
                      "single dashes, 3 to 36 characters)")

    def number(name, lo, hi):
        text = (row.get(name) or "").strip().replace(",", ".")      # accept 46,52 (Excel in French)
        try:
            v = float(text)
        except ValueError:
            errors.append(f"{name} '{text}' is not a number")
            return None
        if not lo <= v <= hi:
            errors.append(f"{name} {v} is outside [{lo}, {hi}]")
        return v

    lat = number("lat", -90, 90)
    lon = number("lon", -180, 180)
    height = number("height_m", 0, MAX_HEIGHT_M)

    if lat is not None and lon is not None:
        la0, la1, lo0, lo1 = SWITZERLAND
        if not (la0 <= lat <= la1 and lo0 <= lon <= lo1):
            hint = " (lat and lon swapped?)" if la0 <= lon <= la1 and lo0 <= lat <= lo1 else ""
            warnings.append(f"{dev}: position {lat}, {lon} is not in Switzerland{hint}")

    installed = None
    text = (row.get("installed_at") or "").strip()
    if text:
        try:
            installed = datetime.fromisoformat(text)
            if installed.tzinfo is None:
                installed = installed.replace(tzinfo=timezone.utc)
        except ValueError:
            errors.append(f"installed_at '{text}' is not a date like 2026-12-01 or 2026-12-01T14:30")

    if errors:
        return None, errors, warnings
    return SensorMeta(dev, lat, lon, height, (row.get("site_description") or "").strip(), installed), [], warnings


def read_csv(path: Path) -> tuple[list[SensorMeta], list[str], list[str]]:
    """All sensors of a CSV file -> (sensors, errors with line numbers, warnings)."""
    text = path.read_text(encoding="utf-8-sig")                     # utf-8-sig: files saved by Excel
    dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;") if text.strip() else csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    missing = [c for c in ("device_id", "lat", "lon", "height_m") if c not in (reader.fieldnames or [])]
    if missing:
        return [], [f"missing column(s): {', '.join(missing)} (expected: {', '.join(COLUMNS)})"], []

    sensors, errors, warnings, seen = [], [], [], {}
    for line, row in enumerate(reader, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue                                                 # empty line
        s, errs, warns = parse_sensor(row)
        errors += [f"line {line}: {e}" for e in errs]
        warnings += [f"line {line}: {w}" for w in warns]
        if s is not None:
            if s.device_id in seen:
                errors.append(f"line {line}: {s.device_id} already on line {seen[s.device_id]}")
            seen[s.device_id] = line
            sensors.append(s)
    return sensors, errors, warnings


def register(repo: Repository, sensors: list[SensorMeta]) -> tuple[int, int]:
    """Saves the sensors. Returns (new, updated)."""
    existing = set(repo.load_sensors()["device_id"])
    for s in sensors:
        repo.save_sensor(s)
    new = sum(s.device_id not in existing for s in sensors)
    return new, len(sensors) - new


def print_sensors(repo: Repository) -> None:
    df = repo.load_sensors()
    if df.empty:
        print("No sensor registered yet.")
        return
    print(df.to_string(index=False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", type=Path, help="CSV file with one sensor per line")
    ap.add_argument("--db", default=SETTINGS.db_path, help="database file (default: %(default)s)")
    ap.add_argument("--list", action="store_true", help="show the registered sensors")
    ap.add_argument("--add", metavar="DEVICE_ID", help="register one sensor from the command line")
    ap.add_argument("--lat")
    ap.add_argument("--lon")
    ap.add_argument("--height", default="")
    ap.add_argument("--site", default="")
    ap.add_argument("--installed", default="")
    args = ap.parse_args(argv)

    if not (args.csv or args.add or args.list):
        ap.print_help()
        return 1
    repo = Repository(args.db)

    if args.csv or args.add:
        if args.csv:
            if not args.csv.exists():
                print(f"{args.csv} not found")
                return 1
            sensors, errors, warnings = read_csv(args.csv)
        else:
            s, errors, warnings = parse_sensor(dict(
                device_id=args.add, lat=args.lat, lon=args.lon, height_m=args.height,
                site_description=args.site, installed_at=args.installed))
            sensors = [s] if s else []
        for w in warnings:
            print("WARNING", w)
        if errors:
            for e in errors:
                print("ERROR  ", e)
            print("Nothing was written. Fix the errors and run again.")
            return 1
        new, updated = register(repo, sensors)
        print(f"{new} sensor(s) added, {updated} updated in {args.db}")

    if args.list:
        print_sensors(repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
