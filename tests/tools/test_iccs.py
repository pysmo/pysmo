from __future__ import annotations
from tests.conftest import TESTDATA
from pysmo.classes import SAC
from pysmo.functions import clone_to_mini
from pysmo.tools.iccs import ICCS, ICCSSeismogram, MiniICCSSeismogram, plotstack
from datetime import timedelta
from typing import TYPE_CHECKING
import pytest

if TYPE_CHECKING:
    from matplotlib.figure import Figure


@pytest.fixture()
def iccs_data() -> list[MiniICCSSeismogram]:
    seismograms: list[MiniICCSSeismogram] = []
    for index, iccs_file in enumerate(TESTDATA["iccs_files"]):
        sac = SAC.from_file(iccs_file)
        update = {"t0": sac.timestamps.t0}
        iccs_seis = clone_to_mini(MiniICCSSeismogram, sac.seismogram, update=update)
        if index == 0:
            iccs_seis.data *= -1
        if index == 1:
            iccs_seis.t0 += timedelta(seconds=-1)
        if index == 2:
            iccs_seis.t0 += timedelta(seconds=1)
        seismograms.append(iccs_seis)
    return seismograms


class TestICCS:
    TAPER = 0.0
    AUTOFLIP = False
    AUTOSELECT = False

    @pytest.fixture(autouse=True, scope="function")
    def _iccs(self, iccs_data: list[ICCSSeismogram]) -> None:
        self.iccs = ICCS(iccs_data)
        self.iccs.taper_width = self.TAPER


class TestICCSNoTaper(TestICCS):
    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_initial.png",
        baseline_dir="../baseline/",
        remove_text=True,
        style="default",
    )
    def test_iccs_stack_initial(self) -> Figure:
        return plotstack(self.iccs)

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_after.png",
        baseline_dir="../baseline/",
        remove_text=True,
        style="default",
    )
    def test_iccs_call(self) -> Figure:
        self.iccs(autoflip=self.AUTOFLIP, autoselect=self.AUTOSELECT)
        return plotstack(self.iccs)


class TestICCSTaper(TestICCS):
    TAPER = 0.1

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_initial_taper.png",
        baseline_dir="../baseline/",
        remove_text=True,
        style="default",
    )
    def test_iccs_stack_initial(self) -> Figure:
        return plotstack(self.iccs)

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_after_taper.png",
        baseline_dir="../baseline/",
        remove_text=True,
        style="default",
    )
    def test_iccs_call(self) -> Figure:
        self.iccs(autoflip=self.AUTOFLIP, autoselect=self.AUTOSELECT)
        return plotstack(self.iccs)


class TestICCSAbsMax(TestICCS):
    AUTOFLIP = True

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_initial_absmax.png",
        baseline_dir="../baseline/",
        remove_text=True,
        style="default",
    )
    def test_iccs_stack_initial(self) -> Figure:
        return plotstack(self.iccs)

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_after_absmax.png",
        baseline_dir="../baseline/",
        remove_text=True,
        style="default",
    )
    def test_iccs_call(self) -> Figure:
        self.iccs(autoflip=self.AUTOFLIP, autoselect=self.AUTOSELECT)
        return plotstack(self.iccs)
