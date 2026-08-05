"""Fetch pysmo's reference event/station bundle from EarthScope.

Downloads IU.ANMO (BHZ and LHZ) recording the 2010-02-27 Maule, Chile M8.8
earthquake, in every format the EarthScope web services offer, as raw
bytes/text — never parsed and re-serialised through pysmo's own classes.
This keeps every fixture an independent, externally-produced ground truth,
rather than round-tripping through the exact code the fixtures are meant to
help validate.

Re-run this script (`python fetch_reference_event.py` from this directory)
to regenerate the bundle from scratch. See PROVENANCE.md for the event/
station details and rationale for this specific choice.
"""

import io
import zipfile
from pathlib import Path

import pandas as pd

from pysmo import MiniEvent, MiniStation
from pysmo.lib.http import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    http_get,
)
from pysmo.tools.azdist import distance, haversine
from pysmo.tools.web import (
    fetch_geocsvseismogram,
    fetch_sacpz,
    fetch_stationxml,
    fetch_travel_times,
)

OUTPUT_DIR = Path(__file__).parent

# fdsnws/dataselect has no public pysmo.tools.web wrapper (it's used
# internally by fetch_geocsvseismogram for format="geocsv" only), and this
# script is external to the pysmo package, so it isn't meant to reach into
# tools.web's private _EarthScopeDefaults for the URL. Only the numeric
# retry/timeout defaults, already public in pysmo.lib.http, are reused.
DATASELECT_URL = "https://service.earthscope.org/fdsnws/dataselect/1/query"

EVENT = MiniEvent(
    latitude=-36.122,
    longitude=-72.898,
    depth=22900.0,
    time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
)

STATIONS = {
    "bhz": MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="BHZ",
        latitude=34.945981,
        longitude=-106.457133,
    ),
    "lhz": MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="LHZ",
        latitude=34.945981,
        longitude=-106.457133,
    ),
}


def _fetch_raw_waveform(
    station: MiniStation,
    starttime: pd.Timestamp,
    endtime: pd.Timestamp,
    format: str,
) -> bytes:
    return http_get(
        DATASELECT_URL,
        {
            "net": station.network,
            "sta": station.name,
            "loc": station.location,
            "cha": station.channel,
            "starttime": starttime.isoformat(),
            "endtime": endtime.isoformat(),
            "format": format,
        },
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        request_retries=DEFAULT_REQUEST_RETRIES,
        retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
    )


def _extract_single_sac(archive_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        if len(names) != 1:
            raise ValueError(f"Expected exactly one file in SAC archive, got {names}")
        return archive.read(names[0])


def main() -> None:
    reference_station = STATIONS["bhz"]
    dist_deg = haversine(EVENT, reference_station)
    dist_km = distance(EVENT, reference_station) / 1000.0
    travel_times = fetch_travel_times(EVENT.depth / 1000.0, dist_deg, ["P"])
    predicted_p = EVENT.time + pd.Timedelta(seconds=travel_times["P"])
    starttime = predicted_p - pd.Timedelta(minutes=2)

    # Window end is anchored to the *origin* time via surface-wave group
    # velocity, not to the predicted P arrival: for a large, shallow event
    # like this one, surface waves (often the largest-amplitude phase of
    # the whole recording) arrive tens of minutes after P, well outside any
    # P-relative window. 3.0 km/s is a conservative (slow) bound on the
    # fundamental-mode Rayleigh/Love dispersion train's group velocity, so
    # this covers the full dispersed wave train, not just its fast onset;
    # +10 minutes gives some coda after that.
    surface_wave_seconds = dist_km / 3.0
    endtime = (
        EVENT.time
        + pd.Timedelta(seconds=surface_wave_seconds)
        + pd.Timedelta(minutes=10)
    )

    for label, station in STATIONS.items():
        (OUTPUT_DIR / f"iu_anmo_00_{label}_response.xml").write_bytes(
            fetch_stationxml(station=station)
        )
        (OUTPUT_DIR / f"iu_anmo_00_{label}.pz").write_text(
            # irisws/sacpz rejects fractional seconds in `time` (HTTP 500,
            # "For input string" — confirmed directly against the live
            # service), unlike fdsnws/dataselect used for the waveforms
            # below, so floor to whole seconds for this call only.
            fetch_sacpz(station=station, time=starttime.floor("s"))
        )
        (OUTPUT_DIR / f"iu_anmo_00_{label}.geocsv").write_bytes(
            fetch_geocsvseismogram(
                station=station, starttime=starttime, endtime=endtime
            )
        )
        (OUTPUT_DIR / f"iu_anmo_00_{label}.mseed").write_bytes(
            _fetch_raw_waveform(station, starttime, endtime, "miniseed")
        )
        sac_zip = _fetch_raw_waveform(station, starttime, endtime, "sac.zip")
        (OUTPUT_DIR / f"iu_anmo_00_{label}.sac").write_bytes(
            _extract_single_sac(sac_zip)
        )
        print(f"Fetched {label.upper()}: {starttime} to {endtime}")


if __name__ == "__main__":
    main()
