"""Live checks against the real EarthScope web services.

These hit the actual network and are skipped by default; run with
`pytest --run-real-web-requests` to opt in. They exist to catch drift
between pysmo's assumptions and the live services (URL, request
parameters, response format) that mocked tests in `test_web.py` cannot.

`test_fetch_seismogram_live` is checked with pytest-mpl against a
baseline plot (the waveform with the predicted P arrival marked) rather
than a syrupy snapshot: syrupy fails the whole test session on any
*unused* snapshot, and this test's snapshot would always be unused in a
normal (non-live) run, breaking every default `make tests`/CI run.
pytest-mpl's image comparison doesn't have that failure mode, and the
plot doubles as a visual check that the fetched waveform actually looks
like an earthquake, not just that its numbers match. The 2010 Maule
event is archived, historical data, so both the waveform and the
computed arrival time are expected to be stable across runs; a mismatch
signals an upstream data change or a pysmo regression, not flakiness.
Regenerate the baseline with `make test-figs` if a change is expected.
"""

import matplotlib
import pandas as pd
import pytest
from matplotlib.dates import date2num
from matplotlib.figure import Figure

from pysmo import MiniEvent, MiniStation, Response
from pysmo.classes import SAC, GeoCsvSeismogram, SacPZ
from pysmo.functions import detrend
from pysmo.tools.azdist import haversine
from pysmo.tools.plotutils import plotseis
from pysmo.tools.web import fetch_sac, fetch_travel_times

matplotlib.use("Agg")

pytestmark = pytest.mark.real_web_request

# EarthScope's IASP91 traveltime lookup for this depth/distance is a fixed
# model evaluation, not a measurement, so it is expected to be stable across
# runs; drift here signals a change on EarthScope's side, not flakiness.
EXPECTED_TRAVEL_TIMES = {"P": 604.654, "S": 1096.553}


@pytest.fixture()
def station() -> MiniStation:
    return MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="LHZ",
        latitude=34.945981,
        longitude=-106.457133,
    )


@pytest.fixture()
def event() -> MiniEvent:
    return MiniEvent(
        latitude=-36.122,
        longitude=-72.898,
        depth=22900.0,
        time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
    )


def test_fetch_travel_times_live() -> None:
    result = fetch_travel_times(22.9, 60.0, ["P", "S"])

    assert result.keys() >= {"P", "S"}
    assert 0 < result["P"] < result["S"]
    assert {phase: round(t, 3) for phase, t in result.items()} == EXPECTED_TRAVEL_TIMES


@pytest.mark.mpl_image_compare(remove_text=True)
def test_fetch_seismogram_live(station: MiniStation, event: MiniEvent) -> Figure:
    # Computing a phase-relative window is just the predicted arrival time
    # plus/minus a duration — see fetch_travel_times's own Examples.
    dist = haversine(event, station)
    travel_times = fetch_travel_times(event.depth / 1000.0, dist, ["P"])
    predicted_p = event.time + pd.Timedelta(seconds=travel_times["P"])

    seismogram = GeoCsvSeismogram.fetch(
        station=station,
        starttime=predicted_p - pd.Timedelta(minutes=2),
        endtime=predicted_p + pd.Timedelta(minutes=8),
    )

    assert isinstance(seismogram, GeoCsvSeismogram)
    assert seismogram.sid == "IU_ANMO_00_LHZ"
    assert seismogram.delta == pd.Timedelta(seconds=1)
    assert len(seismogram.data) == 600
    assert seismogram.begin_time < predicted_p < seismogram.end_time

    detrend(seismogram)
    fig = plotseis(seismogram, showfig=False, linewidth=0.5)
    fig.gca().axvline(
        date2num(predicted_p), color="red", linestyle="--", label="predicted P"
    )
    fig.gca().legend(loc="upper right")
    return fig


def test_fetch_sacpz_live(station: MiniStation) -> None:
    response = SacPZ.fetch(station=station)

    assert isinstance(response, Response)
    assert response.network == "IU"
    assert response.station == "ANMO"
    assert response.channel == "LHZ"
    assert len(response.poles) > 0
    assert response.overall_sensitivity != 0


def test_fetch_sac_live(station: MiniStation, event: MiniEvent) -> None:
    # A phase-relative window is deliberately used (rather than a
    # whole-second literal) so starttime/endtime are fractional-second
    # pd.Timestamps -- exactly the shape fdsnws/dataselect must accept
    # directly via .isoformat(), unlike the retired irisws/timeseries
    # endpoint, which required stripping fractional seconds/UTC offsets
    # before every request.
    dist = haversine(event, station)
    travel_times = fetch_travel_times(event.depth / 1000.0, dist, ["P"])
    predicted_p = event.time + pd.Timedelta(seconds=travel_times["P"])

    sac = SAC.fetch(
        station=station,
        starttime=predicted_p - pd.Timedelta(minutes=2),
        endtime=predicted_p + pd.Timedelta(minutes=8),
    )

    assert isinstance(sac, SAC)
    assert sac.station.network == "IU"
    assert sac.station.name == "ANMO"
    assert sac.station.channel == "LHZ"
    assert sac.seismogram.delta == pd.Timedelta(seconds=1)
    assert len(sac.seismogram.data) == 600
    assert sac.seismogram.begin_time < predicted_p < sac.seismogram.end_time


def test_fetch_sac_multiple_segments_live() -> None:
    # A wildcarded channel matching more than one co-located component is a
    # stable, indefinitely reproducible way to trigger SAC.fetch()'s
    # multi-segment path -- unlike a real data gap, which could close if
    # the archive is ever backfilled. IU.ANMO.00 records three orthogonal
    # BH? components (BH1, BH2, BHZ).
    station = MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="BH?",
        latitude=34.945981,
        longitude=-106.457133,
    )
    starttime = pd.Timestamp("2010-02-27T06:44:00Z")
    endtime = pd.Timestamp("2010-02-27T06:54:00Z")

    with pytest.raises(ValueError, match="3 segments"):
        SAC.fetch(station=station, starttime=starttime, endtime=endtime)

    archive = fetch_sac(station=station, starttime=starttime, endtime=endtime)
    segments = SAC.all_from_zip(archive)

    assert len(segments) == 3
    assert all(isinstance(segment, SAC) for segment in segments)
    assert {segment.station.channel for segment in segments} == {
        "BH1",
        "BH2",
        "BHZ",
    }
