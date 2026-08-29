import os
import shutil
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from pysmo import (
    LocationWithDepth,
    MiniLocationWithDepth,
    MiniSeismogram,
    MiniStation,
    Seismogram,
    Station,
)
from pysmo.classes import SAC, GeoCsvSeismogram, MSeed, SacSeismogram, SacStation


@pytest.fixture()
def assets(reference_event_assets: dict[str, Path]) -> dict[str, Path]:
    return {"orgfile": reference_event_assets["sac_bhz"]}


@pytest.fixture()
def empty_file(tmpdir_factory: pytest.TempdirFactory) -> Path:
    tmpdir = tmpdir_factory.mktemp("empty_files")
    return Path(tmpdir) / "empty_file"


@pytest.fixture()
def sacfile(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, Path]) -> Path:
    orgfile = assets["orgfile"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sac_instance(sacfile: Path) -> SAC:
    return SAC.from_file(sacfile)


@pytest.fixture()
def sac_seismogram(sac_instance: SAC) -> SacSeismogram:
    return sac_instance.seismogram


@pytest.fixture(scope="function")
def mini_seismogram(sac_seismogram: Seismogram) -> MiniSeismogram:
    return MiniSeismogram(
        begin_time=sac_seismogram.begin_time,
        delta=sac_seismogram.delta,
        data=sac_seismogram.data.copy(),
    )


@pytest.fixture(scope="function")
def geocsv_seismogram(sac_seismogram: Seismogram) -> GeoCsvSeismogram:
    return GeoCsvSeismogram(
        begin_time=sac_seismogram.begin_time,
        delta=sac_seismogram.delta,
        data=sac_seismogram.data.copy(),
        sourceid="XX_TEST_00_HHZ",
    )


@pytest.fixture(scope="function")
def mseed_seismogram(reference_event_assets: dict[str, Path]) -> MSeed:
    return MSeed.from_file(reference_event_assets["mseed_bhz"])


@pytest.fixture()
def seismograms(
    sac_seismogram: Seismogram, mini_seismogram: Seismogram
) -> list[Seismogram]:
    return [sac_seismogram, mini_seismogram]


SEISMOGRAM_FIXTURE_NAMES = [
    "sac_seismogram",
    "mini_seismogram",
    "geocsv_seismogram",
    "mseed_seismogram",
]


@pytest.fixture(params=SEISMOGRAM_FIXTURE_NAMES, ids=SEISMOGRAM_FIXTURE_NAMES)
def seismogram(request: pytest.FixtureRequest) -> Seismogram:
    """A Seismogram, parametrized across every concrete implementation.

    To add a new concrete class to this matrix: add a fixture for it above,
    then append its name to SEISMOGRAM_FIXTURE_NAMES.
    """
    return request.getfixturevalue(request.param)


@pytest.fixture()
def sac_station(sac_instance: SAC) -> SacStation:
    return sac_instance.station


@pytest.fixture()
def mini_station(sac_station: Station) -> MiniStation:
    return MiniStation(
        name=sac_station.name,
        network=sac_station.network,
        location=sac_station.location,
        channel=sac_station.channel,
        latitude=sac_station.latitude,
        longitude=sac_station.longitude,
        elevation=sac_station.elevation,
    )


@pytest.fixture()
def stations(sac_station: Station, mini_station: Station) -> tuple[Station, ...]:
    return sac_station, mini_station


@pytest.fixture()
def sac_event(sac_instance: SAC):  # type: ignore
    return sac_instance.event


@pytest.fixture()
def mini_hypocenter(sac_event) -> MiniLocationWithDepth:  # type: ignore
    return MiniLocationWithDepth(
        latitude=sac_event.latitude,
        longitude=sac_event.longitude,
        depth=sac_event.depth,
    )


@pytest.fixture()
def hypocenters(
    sac_event: LocationWithDepth, mini_hypocenter: LocationWithDepth
) -> tuple[LocationWithDepth, ...]:
    return sac_event, mini_hypocenter


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-real-web-requests",
        action="store_true",
        default=False,
        help="run tests marked 'real_web_request', which hit live web services.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: Sequence[pytest.Item]
) -> None:
    if config.getoption("--run-real-web-requests"):
        return
    skip_real_web_request = pytest.mark.skip(
        reason="need --run-real-web-requests option to run"
    )
    for item in items:
        if "real_web_request" in item.keywords:
            item.add_marker(skip_real_web_request)


def pytest_configure(config: pytest.Config) -> None:
    hypothesis_settings.register_profile("ci", max_examples=100, deadline=None)
    hypothesis_settings.register_profile("dev", max_examples=50, deadline=None)
    hypothesis_settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))


# Realistic sampling intervals in seconds
_DELTA_STRATEGY = st.sampled_from(
    [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
)


@composite
def mini_seismograms(
    draw: st.DrawFn,
    min_length: int = 10,
    max_length: int = 500,
) -> MiniSeismogram:
    """Draw a valid MiniSeismogram with bounded random data, begin_time, and delta."""
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    data = draw(
        st.lists(
            st.floats(
                min_value=-1e6,
                max_value=1e6,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=length,
            max_size=length,
        )
    )
    delta = draw(_DELTA_STRATEGY)
    begin_time = draw(
        st.datetimes(
            min_value=datetime(1970, 1, 1),
            max_value=datetime(2030, 1, 1),
            timezones=st.just(timezone.utc),
        )
    )
    return MiniSeismogram(
        data=np.array(data, dtype=np.float64),
        delta=pd.Timedelta(seconds=delta),
        begin_time=pd.Timestamp(begin_time),
    )


@composite
def contiguous_seismogram_pairs(
    draw: st.DrawFn,
    min_length: int = 10,
    max_length: int = 250,
) -> tuple[MiniSeismogram, MiniSeismogram]:
    """Draw two contiguous MiniSeismograms sharing the same delta without gaps."""
    seis1 = draw(mini_seismograms(min_length=min_length, max_length=max_length))
    length2 = draw(st.integers(min_value=min_length, max_value=max_length))
    data2 = draw(
        st.lists(
            st.floats(
                min_value=-1e6,
                max_value=1e6,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=length2,
            max_size=length2,
        )
    )
    seis2 = MiniSeismogram(
        data=np.array(data2, dtype=np.float64),
        delta=seis1.delta,
        begin_time=seis1.end_time + seis1.delta,
    )
    return seis1, seis2
