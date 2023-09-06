import pytest
from pysmo import (
    SAC,
    Seismogram,
    Station,
    MiniSeismogram,
    MiniStation,
    MiniHypocenter,
    Hypocenter
)


@pytest.fixture()
def sac_instance(sacfile: str) -> SAC:
    """Returns a SAC instance created from testfile.sac"""
    return SAC.from_file(sacfile)


@pytest.fixture()
def sac_seismogram(sac_instance: SAC) -> Seismogram:
    return sac_instance.seismogram


@pytest.fixture(scope="function")
def mini_seismogram(sac_seismogram: Seismogram) -> Seismogram:
    return MiniSeismogram(begin_time=sac_seismogram.begin_time, sampling_rate=sac_seismogram.sampling_rate,
                          data=sac_seismogram.data)


@pytest.fixture()
def seismograms(sac_seismogram: Seismogram, mini_seismogram: Seismogram) -> list[Seismogram]:
    return [sac_seismogram, mini_seismogram]


@pytest.fixture()
def sac_station(sac_instance: SAC) -> Station:
    return sac_instance.station


@pytest.fixture()
def mini_station(sac_station: Station) -> Station:
    return MiniStation(latitude=sac_station.latitude, longitude=sac_station.longitude, name=sac_station.name,
                       elevation=sac_station.elevation, network=sac_station.network)


@pytest.fixture()
def stations(sac_station: Station, mini_station: Station) -> tuple[Station, ...]:
    return sac_station, mini_station


@pytest.fixture()
def sac_event(sac_instance: SAC):  # type: ignore
    return sac_instance.event


@pytest.fixture()
def mini_hypocenter(sac_event) -> Hypocenter:  # type:ignore
    return MiniHypocenter(latitude=sac_event.latitude, longitude=sac_event.longitude, depth=sac_event.depth)


@pytest.fixture()
def hypocenters(sac_event: Hypocenter, mini_hypocenter: Hypocenter) -> tuple[Hypocenter, ...]:
    return sac_event, mini_hypocenter
