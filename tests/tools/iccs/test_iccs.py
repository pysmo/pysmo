from __future__ import annotations
from pysmo import MiniSeismogram
from pysmo.tools.iccs import ICCS, ICCSSeismogram, plotstack
from typing import TYPE_CHECKING
from datetime import timedelta
import pytest

from pysmo.tools.iccs._iccs import CONVERGENCE_METHOD

if TYPE_CHECKING:
    from matplotlib.figure import Figure


class TestICCSBase:
    TAPER: float = 0.0
    AUTOFLIP: bool = False
    AUTOSELECT: bool = False
    PARALLEL: bool = False
    METHOD: CONVERGENCE_METHOD = "corrcoef"
    PADDED_FIG: bool = False

    @pytest.fixture(autouse=True, scope="function")
    def _iccs(self, iccs_seismograms: list[ICCSSeismogram]) -> None:
        self.iccs = ICCS(iccs_seismograms)
        self.iccs.taper_width = self.TAPER

    @pytest.mark.mpl_image_compare(
        remove_text=True,
        style="default",
    )
    def test_iccs_stack_initial(self) -> Figure:
        fig, _ = plotstack(self.iccs, padded=self.PADDED_FIG, return_fig=True)
        return fig

    @pytest.mark.mpl_image_compare(
        remove_text=True,
        style="default",
    )
    def test_iccs_call(self) -> Figure:
        self.iccs(
            autoflip=self.AUTOFLIP,
            autoselect=self.AUTOSELECT,
            parallel=self.PARALLEL,
            convergence_method=self.METHOD,
        )
        fig, _ = plotstack(self.iccs, padded=False, return_fig=True)
        return fig


class TestICCSTaper(TestICCSBase):
    TAPER: float = 0.1


class TestICCSAutoflip(TestICCSBase):
    AUTOFLIP: bool = True


class TestICCSParallel(TestICCSBase):
    PARALLEL: bool = True


class TestICCSMethod(TestICCSBase):
    METHOD: CONVERGENCE_METHOD = "change"


class TestICCSPaddedFig(TestICCSBase):
    PADDED_FIG: bool = True


class TestICCSParameters(TestICCSBase):
    """Test changing parameters."""

    def test_cached_data(self) -> None:
        self.iccs._clear_caches()
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

    def test_change_timewindow(self) -> None:
        assert self.iccs.window_pre.total_seconds() == -10
        with pytest.raises(ValueError):
            self.iccs.window_pre += timedelta(seconds=11)
        self.iccs.window_pre += timedelta(seconds=2.34)
        assert self.iccs.window_pre.total_seconds() == -7.66
