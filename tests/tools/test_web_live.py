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

from pysmo import MiniEvent, MiniStation
from pysmo.classes import SAC, GeoCsvSeismogram, MSeed, QuakeML, SacPZ
from pysmo.functions import detrend
from pysmo.tools.azdist import haversine
from pysmo.tools.plotutils import plotseis
from pysmo.tools.traveltime import travel_times
from pysmo.tools.web import fetch_mseed, fetch_sac, fetch_station_inventory

matplotlib.use("Agg")

pytestmark = pytest.mark.real_web_request


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


@pytest.mark.mpl_image_compare(remove_text=True)
def test_fetch_seismogram_live(station: MiniStation, event: MiniEvent) -> Figure:
    # Computing a phase-relative window is just the predicted arrival time
    # plus/minus a duration — see travel_times's own Examples.
    dist = haversine(event, station)
    arrivals = travel_times(depth=event.depth, distance=dist, phases=["P"])
    predicted_p = event.time + arrivals["P"]

    seismogram = GeoCsvSeismogram.fetch(
        station=station,
        starttime=predicted_p - pd.Timedelta(minutes=2),
        endtime=predicted_p + pd.Timedelta(minutes=8),
    )

    assert isinstance(seismogram, GeoCsvSeismogram)
    assert seismogram.sourceid == "IU_ANMO_00_LHZ"
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
    arrivals = travel_times(depth=event.depth, distance=dist, phases=["P"])
    predicted_p = event.time + arrivals["P"]

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


def test_fetch_mseed_live(station: MiniStation) -> None:
    # A fractional-second window (rather than a whole-second literal) so
    # starttime/endtime reach dataselect as fractional-second
    # pd.Timestamps via .isoformat() -- the shape fdsnws/dataselect must
    # accept directly.
    starttime = pd.Timestamp("2010-02-27T06:44:06.069538Z")
    endtime = starttime + pd.Timedelta(minutes=10)

    seismogram = MSeed.fetch(station=station, starttime=starttime, endtime=endtime)

    assert isinstance(seismogram, MSeed)
    assert seismogram.sourceid == "FDSN:IU_ANMO_00_L_H_Z"
    assert (seismogram.network, seismogram.name, seismogram.channel) == (
        "IU",
        "ANMO",
        "LHZ",
    )
    assert seismogram.delta == pd.Timedelta(seconds=1)
    assert 595 < len(seismogram.data) <= 601
    assert seismogram.begin_time >= starttime
    assert seismogram.end_time <= endtime


def test_fetch_mseed_multiple_segments_live() -> None:
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

    with pytest.raises(ValueError, match="contiguous segments"):
        MSeed.fetch(station=station, starttime=starttime, endtime=endtime)

    raw = fetch_mseed(station=station, starttime=starttime, endtime=endtime)
    segments = MSeed.all_from_bytes(raw)

    assert len(segments) == 3
    assert {segment.channel for segment in segments} == {"BH1", "BH2", "BHZ"}


def test_fetch_quakeml_single_event_live() -> None:
    event = QuakeML.fetch(event_id="official20100227063411530_30")

    assert event.magnitude is not None and event.magnitude >= 8.5
    assert event.time.year == 2010


def test_fetch_quakeml_catalogue_live() -> None:
    events = QuakeML.all_from_query(
        starttime=pd.Timestamp("2010-02-27T00:00:00Z"),
        endtime=pd.Timestamp("2010-02-28T00:00:00Z"),
        minmagnitude=7.0,
    )

    assert len(events) >= 1
    assert all(e.magnitude is None or e.magnitude >= 7.0 for e in events)


def test_fetch_station_inventory_live() -> None:
    xml = fetch_station_inventory(network="IU", station="ANMO,COLA", channel="BH?")

    assert b"FDSNStationXML" in xml
