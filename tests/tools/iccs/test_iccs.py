from __future__ import annotations
from pysmo.tools.iccs import ICCS, ICCSSeismogram, plot_stack
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
        fig, _ = plot_stack(self.iccs, padded=self.PADDED_FIG, return_fig=True)
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
        fig, _ = plot_stack(self.iccs, padded=False, return_fig=True)
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
    """Test changing parameters and methods (other than __call__)."""

    def test_change_timewindow(self) -> None:
        assert self.iccs.window_pre.total_seconds() == -10
        with pytest.raises(ValueError):
            self.iccs.window_pre = timedelta(seconds=1)
        self.iccs.window_pre += timedelta(seconds=2.34)
        assert self.iccs.window_pre.total_seconds() == -7.66

    def test_invalid_window_pre(self) -> None:
        max_window_pre = max(
            s.begin_time - (s.t1 or s.t0) for s in self.iccs.seismograms if s.select
        )
        with pytest.raises(ValueError):
            self.iccs.window_pre -= timedelta(seconds=1) + max_window_pre

    def test_invalid_window_post(self) -> None:
        min_window_post = min(
            (s.t1 or s.t0) - s.end_time for s in self.iccs.seismograms if s.select
        )
        with pytest.raises(ValueError):
            self.iccs.window_post += timedelta(seconds=1) + min_window_post

    def test_validate_pick(self) -> None:
        from pysmo.tools.iccs._iccs import _calc_valid_pick_range

        min_pick, max_pick = _calc_valid_pick_range(self.iccs)

        assert self.iccs.validate_pick(min_pick) is True
        assert self.iccs.validate_pick(max_pick) is True
        assert self.iccs.validate_pick(min_pick - timedelta(seconds=0.01)) is False
        assert self.iccs.validate_pick(max_pick + timedelta(seconds=0.01)) is False

    def test_validate_time_window(self) -> None:
        from pysmo.tools.iccs._iccs import _calc_valid_time_window_range

        min_window_pre, max_window_post = _calc_valid_time_window_range(self.iccs)

        assert self.iccs.validate_time_window(min_window_pre, max_window_post) is True
        assert self.iccs.validate_time_window(max_window_post, min_window_pre) is False
        assert (
            self.iccs.validate_time_window(-self.iccs.stack.delta / 2, max_window_post)
            is False
        )
        assert (
            self.iccs.validate_time_window(min_window_pre, self.iccs.stack.delta / 2)
            is False
        )
        assert (
            self.iccs.validate_time_window(
                min_window_pre - timedelta(seconds=0.01), max_window_post
            )
            is False
        )
        assert (
            self.iccs.validate_time_window(
                min_window_pre, max_window_post + timedelta(seconds=0.01)
            )
            is False
        )
