"""Copy this directory's ICCS fixture files from a data-example checkout.

Copies already-fetched, already-annotated `NET.STA.LOC.BHZ` files from
`data-example`'s `fiji_region` event into this directory, renamed to the
`net_sta.bhz` convention this fixture uses. Byte-for-byte copy, not a
re-fetch — no second round-trip through pysmo's writer.

Re-run this script (`uv run python derive_fixture.py --data-example-path
<path>` from this directory) if data-example's branch content changes
upstream.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

EVENT_DIR = "Event_2014.11.01.18.57.22.380"

# (network, station, location) for the stations included in this fixture.
STATIONS = [
    ("AK", "ANM", "--"),
    ("AK", "BARN", "--"),
    ("AK", "BPAW", "--"),
    ("AK", "BRSE", "--"),
    ("AK", "DHY", "--"),
    ("AK", "FID", "--"),
    ("AK", "GAMB", "--"),
    ("AK", "GOAT", "--"),
    ("AK", "GRIN", "--"),
    ("AK", "KIAG", "--"),
    ("AK", "KLU", "--"),
    ("AK", "KTH", "--"),
    ("AK", "MCAR", "--"),
    ("AK", "MDM", "--"),
    ("AK", "MESA", "--"),
    ("AK", "PAX", "--"),
    ("AK", "PPD", "--"),
    ("AK", "PTPK", "--"),
    ("AK", "SCM", "--"),
    ("AK", "WAT6", "--"),
    ("AV", "IVE", "--"),
    ("TA", "A21K", "--"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-example-path",
        type=Path,
        default=Path(__file__).parents[5] / "data-example",
        help="Path to a local data-example checkout (default: sibling repo).",
    )
    args = parser.parse_args()

    event_dir = args.data_example_path / EVENT_DIR
    if not event_dir.is_dir():
        raise SystemExit(f"Event directory not found: {event_dir}")

    this_dir = Path(__file__).parent
    for old in this_dir.glob("*.bhz"):
        old.unlink()

    for network, station, location in STATIONS:
        source = event_dir / f"{network}.{station}.{location}.BHZ"
        dest = this_dir / f"{network.lower()}_{station.lower()}.bhz"
        shutil.copyfile(source, dest)
        print(f"copied {source.name} -> {dest.name}")


if __name__ == "__main__":
    main()
