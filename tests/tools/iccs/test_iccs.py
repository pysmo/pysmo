from __future__ import annotations
from pysmo import MiniSeismogram
from pysmo.tools.iccs import ICCS, ICCSSeismogram, plotstack
from typing import TYPE_CHECKING
from datetime import timedelta
import pytest

if TYPE_CHECKING:
    from matplotlib.figure import Figure

BASELINE_DIR = "../../baseline/"


class TestICCS:
    TAPER: float = 0.0
    AUTOFLIP: bool = False
    AUTOSELECT: bool = False

    @pytest.fixture(autouse=True, scope="function")
    def _iccs(self, iccs_seismograms: list[ICCSSeismogram]) -> None:
        self.iccs = ICCS(iccs_seismograms)
        self.iccs.taper_width = self.TAPER


class TestICCSParameters(TestICCS):
    """Test changing parameters."""

    def test_cached_data(self) -> None:
        assert self.iccs._seismograms_prepared is None
        assert self.iccs._seismograms_for_plotting is None
        assert self.iccs._seismograms_ccnorm is None
        assert self.iccs._stack is None
        assert self.iccs._stack_for_plotting is None

        assert isinstance(self.iccs.stack, MiniSeismogram)
        assert isinstance(self.iccs._stack, MiniSeismogram)
        assert isinstance(self.iccs.seismograms_prepared[0], MiniSeismogram)

        assert isinstance(self.iccs.stack_for_plotting, MiniSeismogram)
        assert isinstance(self.iccs._stack_for_plotting, MiniSeismogram)
        assert isinstance(self.iccs.seismograms_for_plotting[0], MiniSeismogram)

        assert isinstance(self.iccs.seismograms_ccnorm[0], float)
        assert isinstance(self.iccs._seismograms_ccnorm[0], float)

        self.iccs._clear_caches()
        assert self.iccs._seismograms_prepared is None
        assert self.iccs._seismograms_for_plotting is None
        assert self.iccs._seismograms_ccnorm is None
        assert self.iccs._stack is None
        assert self.iccs._stack_for_plotting is None

    def test_change_timewindow(self) -> None:
        assert self.iccs.window_pre.total_seconds() == -10
        with pytest.raises(ValueError):
            self.iccs.window_pre += timedelta(seconds=11)
        self.iccs.window_pre += timedelta(seconds=2.34)
        assert self.iccs.window_pre.total_seconds() == -7.66


class TestICCSNoTaper(TestICCS):
    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_initial.png",
        baseline_dir=BASELINE_DIR,
        remove_text=True,
        style="default",
    )
    def test_iccs_stack_initial(self) -> Figure:
        fig, _ = plotstack(self.iccs, return_fig=True)
        return fig

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_after.png",
        baseline_dir=BASELINE_DIR,
        remove_text=True,
        style="default",
    )
    def test_iccs_call(self) -> Figure:
        self.iccs(autoflip=self.AUTOFLIP, autoselect=self.AUTOSELECT)
        fig, _ = plotstack(self.iccs, return_fig=True)
        return fig


class TestICCSTaper(TestICCS):
    TAPER: float = 0.1

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_initial_taper.png",
        baseline_dir=BASELINE_DIR,
        remove_text=True,
        style="default",
    )
    def test_iccs_stack_initial(self) -> Figure:
        fig, _ = plotstack(self.iccs, return_fig=True)
        return fig

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_after_taper.png",
        baseline_dir=BASELINE_DIR,
        remove_text=True,
        style="default",
    )
    def test_iccs_call(self) -> Figure:
        self.iccs(autoflip=self.AUTOFLIP, autoselect=self.AUTOSELECT)
        fig, _ = plotstack(self.iccs, return_fig=True)
        return fig


class TestICCSAbsMax(TestICCS):
    AUTOFLIP: bool = True

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_initial_absmax.png",
        baseline_dir=BASELINE_DIR,
        remove_text=True,
        style="default",
    )
    def test_iccs_stack_initial(self) -> Figure:
        fig, _ = plotstack(self.iccs, return_fig=True)
        return fig

    @pytest.mark.mpl_image_compare(
        filename="test_iccs_stack_after_absmax.png",
        baseline_dir=BASELINE_DIR,
        remove_text=True,
        style="default",
    )
    def test_iccs_call(self) -> Figure:
        self.iccs(autoflip=self.AUTOFLIP, autoselect=self.AUTOSELECT)
        fig, _ = plotstack(self.iccs, return_fig=True)
        return fig
