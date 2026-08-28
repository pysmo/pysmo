"""Live integration test: the full instrument-response-removal pipeline.

Chains multiple pysmo modules against the real EarthScope web services —
computing a phase-relative window (via
[`haversine`][pysmo.tools.azdist.haversine] and
[`fetch_travel_times`][pysmo.tools.web.fetch_travel_times] — see that
function's own Examples), fetching a real waveform for it
([`GeoCsvSeismogram.fetch`][pysmo.classes.GeoCsvSeismogram.fetch]) and its
real instrument response
([`StationXML.fetch`][pysmo.classes.StationXML.fetch]),
detrending/tapering it ([`pysmo.functions`][pysmo.functions]), then removing
the response via both the sensitivity-only and full-deconvolution paths
([`remove_response`][pysmo.tools.signal.remove_response]) and plotting the
result ([`plotseis`][pysmo.tools.plotutils.plotseis]) — to catch drift or
regressions in how these pieces compose that unit tests, each exercising one
piece in isolation, cannot.

These hit the actual network and are skipped by default; run with
`pytest --run-real-web-requests` to opt in (see
[`tests/tools/test_web_live.py`][] for the equivalent pattern scoped to
`pysmo.tools.web` alone, including why pytest-mpl rather than a syrupy
snapshot is used here).

The 2010 Maule event recorded at IU.ANMO.00.BHZ is archived, historical data,
so the fetched waveform, response, and downstream numbers are expected to be
stable across runs; a mismatch signals an upstream data change or a pysmo
regression, not flakiness. Regenerate the baseline plot with `make test-figs`
if a change is expected.
"""

import matplotlib
import numpy as np
import pandas as pd
import pytest
from matplotlib.dates import date2num
from matplotlib.figure import Figure

from pysmo import MiniEvent, MiniStation
from pysmo.classes import GeoCsvSeismogram, StationXML
from pysmo.functions import detrend, taper
from pysmo.tools.azdist import haversine
from pysmo.tools.plotutils import plotseis
from pysmo.tools.signal import remove_response
from pysmo.tools.web import fetch_travel_times

matplotlib.use("Agg")

pytestmark = pytest.mark.real_web_request


@pytest.fixture()
def station() -> MiniStation:
    return MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="BHZ",
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
def test_remove_response_pipeline_live(
    station: MiniStation, event: MiniEvent
) -> Figure:
    # Computing a phase-relative window is just the predicted arrival time
    # plus/minus a duration — see fetch_travel_times's own Examples.
    dist = haversine(event, station)
    travel_times = fetch_travel_times(event.depth / 1000.0, dist, ["P"])
    predicted_p = event.time + pd.Timedelta(seconds=travel_times["P"])

    seismogram = GeoCsvSeismogram.fetch(
        station=station,
        starttime=predicted_p - pd.Timedelta(minutes=2),
        endtime=predicted_p + pd.Timedelta(minutes=15),
    )
    epoch = StationXML.fetch(station=station, time=seismogram.begin_time)
    response = epoch.response

    assert epoch.network == "IU"
    assert epoch.name == "ANMO"
    assert epoch.channel == "BHZ"
    assert len(response.stages) > 0

    prepped = detrend(seismogram, clone=True)
    taper(prepped, 0.05)

    nyquist = 0.5 / prepped.delta.total_seconds()
    stage_nyquist = min(stage.input_sample_rate / 2 for stage in response.stages)
    f4 = 0.8 * min(nyquist, stage_nyquist)
    f3 = f4 * 0.9
    f1 = min(abs(pole) for pole in response.poles if pole != 0) / 10
    f2 = f1 * 10
    pre_filt = (f1, f2, f3, f4)

    gain_only = remove_response(prepped, response, clone=True)
    deconvolved = remove_response(prepped, response, pre_filt=pre_filt, clone=True)

    assert np.all(np.isfinite(gain_only.data))
    assert np.all(np.isfinite(deconvolved.data))
    # Sanity range for a large teleseismic P/S wavetrain in velocity (m/s) —
    # not a tight bound, just enough to catch a badly mis-scaled result (e.g.
    # dividing by overall_sensitivity instead of reference_sensitivity, or a
    # similar order-of-magnitude regression).
    assert 1e-5 < np.max(np.abs(deconvolved.data)) < 1e-3
    # Same real earthquake through both response-removal paths: correlated
    # (same underlying signal), but not identical — see remove_response's
    # own docstring examples for why full deconvolution and sensitivity-only
    # division diverge in shape even on a real, well-behaved instrument.
    corr = np.corrcoef(gain_only.data, deconvolved.data)[0, 1]
    assert 0.5 < corr < 1.0
    assert seismogram.begin_time < predicted_p < seismogram.end_time

    fig = plotseis(deconvolved, showfig=False, linewidth=0.5)
    fig.gca().axvline(
        date2num(predicted_p), color="red", linestyle="--", label="predicted P"
    )
    fig.gca().legend(loc="upper right")
    return fig
