from pysmo import (
    Seismogram,
    MiniSeismogram,
    Station,
    MiniStation,
    LocationWithDepth,
    MiniLocationWithDepth,
)
from pysmo.classes import SAC
from pathlib import Path
import pytest
import shutil

TESTDATA = dict(
    orgfile=Path(__file__).parent / "assets/testfile.sac",
    sacfile_IB=Path(__file__).parent / "assets/testfile_iztype_is_IB.sac",
    sacfile_no_b=Path(__file__).parent / "assets/no_b.sac",
    sacfile_v6=Path(__file__).parent / "assets/funcgen6.sac",
    sacfile_v7=Path(__file__).parent / "assets/funcgen7.sac",
    # iccs_files=(sorted((Path(__file__).parent / "assets/iccs/").glob("*.bhz"))),
)


@pytest.fixture()
def assets() -> dict[str, Path]:
    return TESTDATA


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
def sacfile_no_b(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, str]) -> Path:
    orgfile = assets["sacfile_no_b"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_v6(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, str]) -> Path:
    orgfile = assets["sacfile_v6"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_v7(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, str]) -> Path:
    orgfile = assets["sacfile_v7"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sac_seismogram(sac_instance: SAC) -> Seismogram:
    return sac_instance.seismogram


@pytest.fixture(scope="function")
def mini_seismogram(sac_seismogram: Seismogram) -> MiniSeismogram:
    return MiniSeismogram(
        begin_time=sac_seismogram.begin_time,
        delta=sac_seismogram.delta,
        data=sac_seismogram.data,
    )


@pytest.fixture()
def seismograms(
    sac_seismogram: Seismogram, mini_seismogram: Seismogram
) -> list[Seismogram]:
    return [sac_seismogram, mini_seismogram]


@pytest.fixture()
def sac_station(sac_instance: SAC) -> Station:
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
