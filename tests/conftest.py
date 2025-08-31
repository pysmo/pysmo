from __future__ import annotations
from pysmo import (
    Seismogram,
    MiniSeismogram,
    Station,
    MiniStation,
    LocationWithDepth,
    MiniLocationWithDepth,
)
from pysmo.classes import SAC
from typing import TYPE_CHECKING
from glob import glob
import pytest
import os
import shutil

if TYPE_CHECKING:
    from collections.abc import Sequence


TESTDATA = dict(
    orgfile=os.path.join(os.path.dirname(__file__), "assets/testfile.sac"),
    orgfile_special_IB=os.path.join(
        os.path.dirname(__file__), "assets/testfile_iztype_is_IB.sac"
    ),
    bad_no_b=os.path.join(os.path.dirname(__file__), "assets/no_b.sac"),
    funcgen6=os.path.join(os.path.dirname(__file__), "assets/funcgen6.sac"),
    funcgen7=os.path.join(os.path.dirname(__file__), "assets/funcgen7.sac"),
    iccs_files=sorted(
        glob(os.path.join(os.path.dirname(__file__), "assets/iccs/*.bhz"))
    ),
)


@pytest.fixture()
def assets() -> dict[str, str | Sequence[str]]:
    return dict(
        sacfile=TESTDATA["orgfile"],
        sacfile_IB=TESTDATA["orgfile_special_IB"],
        sacfile_no_b=TESTDATA["bad_no_b"],
        sacfile_v6=TESTDATA["funcgen6"],
        sacfile_v7=TESTDATA["funcgen7"],
    )


@pytest.fixture()
def empty_file(tmpdir_factory: pytest.TempdirFactory) -> str:
    tmpdir = tmpdir_factory.mktemp("empty_files")
    return os.path.join(tmpdir, "empty_file")


@pytest.fixture()
def sacfile(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, str]) -> str:
    orgfile = assets["sacfile"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = os.path.join(tmpdir, "testfile.sac")
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sac_instance(sacfile: str) -> SAC:
    return SAC.from_file(sacfile)


@pytest.fixture()
def sacfile_no_b(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, str]) -> str:
    orgfile = assets["sacfile_no_b"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = os.path.join(tmpdir, "testfile.sac")
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_v6(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, str]) -> str:
    orgfile = assets["sacfile_v6"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = os.path.join(tmpdir, "testfile.sac")
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_v7(tmpdir_factory: pytest.TempdirFactory, assets: dict[str, str]) -> str:
    orgfile = assets["sacfile_v7"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = os.path.join(tmpdir, "testfile.sac")
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
        latitude=sac_station.latitude,
        longitude=sac_station.longitude,
        name=sac_station.name,
        elevation=sac_station.elevation,
        network=sac_station.network,
    )


@pytest.fixture()
def stations(sac_station: Station, mini_station: Station) -> tuple[Station, ...]:
    return sac_station, mini_station


@pytest.fixture()
def sac_event(sac_instance: SAC):  # type: ignore
    return sac_instance.event


@pytest.fixture()
def mini_hypocenter(sac_event) -> MiniLocationWithDepth:  # type:ignore
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
