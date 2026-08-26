import pandas as pd
import pytest

from pysmo import MiniEvent, MiniStation


@pytest.fixture()
def station_anmo() -> MiniStation:
    return MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="LHZ",
        latitude=34.945981,
        longitude=-106.457133,
    )


@pytest.fixture()
def station_cacb() -> MiniStation:
    return MiniStation(
        name="CACB",
        network="BL",
        location="00",
        channel="BHZ",
        latitude=-21.680301,
        longitude=-46.732601,
    )


@pytest.fixture()
def event_maule() -> MiniEvent:
    return MiniEvent(
        latitude=-36.122,
        longitude=-72.898,
        depth=22900.0,
        time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
    )


@pytest.fixture()
def event_other() -> MiniEvent:
    return MiniEvent(
        latitude=38.297,
        longitude=142.373,
        depth=29000.0,
        time=pd.Timestamp("2011-03-11T05:46:24.12Z"),
    )
