import re

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from pysmo.tools.iccs import (
    ICCS,
    IccsResult,
    IccsSeismogram,
    McccResult,
    MiniIccsSeismogram,
    plot_stack,
)
from pysmo.tools.iccs._types import ConvergenceMethod


class TestICCSBase:
    TAPER: float = 0.0
    AUTOFLIP: bool = False
    AUTOSELECT: bool = False
    METHOD: ConvergenceMethod = ConvergenceMethod.corrcoef
    CONTEXT_FIG: bool = False

    @pytest.fixture(autouse=True, scope="function")
    def _iccs(self, iccs_seismograms: list[IccsSeismogram]) -> None:
        self.iccs = ICCS(iccs_seismograms)
        self.iccs.ramp_width = self.TAPER

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_iccs_stack_initial(self) -> Figure:
        fig, _ = plot_stack(self.iccs, context=self.CONTEXT_FIG, return_fig=True)
        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_iccs_call(self) -> Figure:
        result = self.iccs(
            autoflip=self.AUTOFLIP,
            autoselect=self.AUTOSELECT,
            convergence_method=self.METHOD,
        )
        assert isinstance(result, IccsResult)
        assert isinstance(result.convergence, np.ndarray)
        assert isinstance(result.converged, bool)
        fig, _ = plot_stack(self.iccs, context=False, return_fig=True)
        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_mccc_call(self) -> Figure:
        results = self.iccs.run_mccc()
        assert isinstance(results, McccResult)
        assert isinstance(results.picks, list)
        assert isinstance(results.picks[0], pd.Timestamp)
        assert isinstance(results.errors, list)
        assert isinstance(results.errors[0], pd.Timedelta)
        assert isinstance(results.rmse, pd.Timedelta)
        assert isinstance(results.cc_means, list)
        assert isinstance(results.cc_stds, list)
        fig, _ = plot_stack(self.iccs, context=False, return_fig=True)
        return fig


class TestICCSTaper(TestICCSBase):
    TAPER: float = 0.1


class TestICCSAutoflip(TestICCSBase):
    AUTOFLIP: bool = True


class TestICCSMethod(TestICCSBase):
    METHOD: ConvergenceMethod = ConvergenceMethod.change


class TestICCSContextFig(TestICCSBase):
    CONTEXT_FIG: bool = True


class TestICCSEmpty:
    """Test ICCS behavior when initialized with no seismograms."""

    def test_init_empty(self) -> None:
        iccs = ICCS()
        assert iccs.seismograms == []
        # Properties should return unconstrained values
        assert iccs.max_td_pre == pd.Timedelta(days=-365 * 100)
        assert iccs.min_td_post == pd.Timedelta(days=365 * 100)
        assert iccs.min_delta == pd.Timedelta(0)

    def test_validate_empty(self) -> None:
        iccs = ICCS()
        # Any reasonable window should be valid when empty
        assert (
            iccs.validate_time_window(
                pd.Timedelta(seconds=-100), pd.Timedelta(seconds=100)
            )
            is True
        )
        assert iccs.validate_pick(pd.Timedelta(seconds=0)) is True

    def test_prepare_empty(self) -> None:
        iccs = ICCS()
        assert iccs.cc_seismograms == []
        assert iccs.context_seismograms == []

    def test_revalidation_on_set_seismograms(
        self, iccs_seismograms: list[IccsSeismogram]
    ) -> None:
        iccs = ICCS()
        # Set an extremely large window that would normally be invalid
        iccs.window_pre = pd.Timedelta(seconds=-10000)

        # Setting seismograms should now trigger validation and fail
        with pytest.raises(ValueError, match="window_pre is too low"):
            iccs.seismograms = iccs_seismograms


class TestICCSParameters(TestICCSBase):
    """Test changing parameters and methods (other than __call__)."""

    def test_change_timewindow(self) -> None:
        assert self.iccs.window_pre.total_seconds() == -15
        with pytest.raises(ValueError):
            self.iccs.window_pre = pd.Timedelta(seconds=1)
        self.iccs.window_pre += pd.Timedelta(seconds=2.34)
        assert self.iccs.window_pre.total_seconds() == -12.66

    def test_invalid_window_pre(self) -> None:
        max_window_pre = max(
            s.begin_time - (s.t1 or s.t0) for s in self.iccs.seismograms
        )
        with pytest.raises(ValueError):
            self.iccs.window_pre -= pd.Timedelta(seconds=1) + max_window_pre

    def test_invalid_window_post(self) -> None:
        min_window_post = min(
            (s.t1 or s.t0) - s.end_time for s in self.iccs.seismograms
        )
        with pytest.raises(ValueError):
            self.iccs.window_post += pd.Timedelta(seconds=1) + min_window_post

    def test_validate_pick(self) -> None:
        from pysmo.tools.iccs._iccs import _calc_valid_pick_range

        min_pick, max_pick = _calc_valid_pick_range(self.iccs)

        assert self.iccs.validate_pick(min_pick) is True
        assert self.iccs.validate_pick(max_pick) is True
        assert self.iccs.validate_pick(min_pick - pd.Timedelta(seconds=0.01)) is False
        assert self.iccs.validate_pick(max_pick + pd.Timedelta(seconds=0.01)) is False

    def test_validate_time_window(self) -> None:
        # With ramp=0 (TAPER=0.0), the valid window extends to exactly the seismogram edges.
        max_td_pre = max(s.begin_time - (s.t1 or s.t0) for s in self.iccs.seismograms)
        min_td_post = min(s.end_time - (s.t1 or s.t0) for s in self.iccs.seismograms)

        assert self.iccs.validate_time_window(max_td_pre, min_td_post) is True
        # Reversed window is invalid.
        assert self.iccs.validate_time_window(min_td_post, max_td_pre) is False
        # window_pre too close to zero (must be <= -min_delta).
        assert (
            self.iccs.validate_time_window(-self.iccs.min_delta / 2, min_td_post)
            is False
        )
        # window_post too close to zero (must be >= min_delta).
        assert (
            self.iccs.validate_time_window(max_td_pre, self.iccs.min_delta / 2) is False
        )
        # Just outside the pre-pick boundary.
        assert (
            self.iccs.validate_time_window(
                max_td_pre - pd.Timedelta(seconds=0.01), min_td_post
            )
            is False
        )
        # Just outside the post-pick boundary.
        assert (
            self.iccs.validate_time_window(
                max_td_pre, min_td_post + pd.Timedelta(seconds=0.01)
            )
            is False
        )

    def test_window_pre_at_exact_boundary(self) -> None:
        """Test that window_pre can be set to exactly the minimum valid value."""
        # With ramp=0, the minimum valid window_pre equals the most constrained
        # seismogram's begin_time to pick gap.
        min_window_pre = max(
            s.begin_time - (s.t1 or s.t0) for s in self.iccs.seismograms
        )
        # Boundary is inclusive — must not raise.
        self.iccs.window_pre = min_window_pre
        assert self.iccs.window_pre == min_window_pre

    def test_window_post_at_exact_boundary(self) -> None:
        """Test that window_post can be set to exactly the maximum valid value."""
        max_window_post = min(
            s.end_time - (s.t1 or s.t0) for s in self.iccs.seismograms
        )
        # Boundary is inclusive — must not raise.
        self.iccs.window_post = max_window_post
        assert self.iccs.window_post == max_window_post

    def test_validate_time_window_consistent_with_attrs(self) -> None:
        """validate_time_window and the attrs validators must agree on boundaries."""
        max_td_pre = max(s.begin_time - (s.t1 or s.t0) for s in self.iccs.seismograms)
        min_td_post = min(s.end_time - (s.t1 or s.t0) for s in self.iccs.seismograms)

        # validate_time_window returns True for the boundary window…
        assert self.iccs.validate_time_window(max_td_pre, min_td_post) is True
        # …and the attrs validators must accept those same values.
        self.iccs.window_pre = max_td_pre
        self.iccs.window_post = min_td_post

    def test_cached_td_properties(self) -> None:
        """Test that max_td_pre and min_td_post are cached and cleared correctly."""
        # First access populates caches.
        max_td_pre = self.iccs.max_td_pre
        min_td_post = self.iccs.min_td_post
        assert self.iccs._max_td_pre_cache is not None
        assert self.iccs._min_td_post_cache is not None
        # Second access returns the same cached value.
        assert self.iccs.max_td_pre == max_td_pre
        assert self.iccs.min_td_post == min_td_post
        # Clearing caches resets them.
        self.iccs.clear_cache()
        assert self.iccs._max_td_pre_cache is None
        assert self.iccs._min_td_post_cache is None

    def test_deselected_seismogram_constrains_valid_window_range(self) -> None:
        """validate_time_window must consider all seismograms regardless of select.

        Even when the most constraining seismogram is deselected,
        validate_time_window must still reject windows that would overflow it,
        because _prepare_seismograms processes all seismograms.
        """
        # Find the seismogram with the smallest gap from begin_time to pick.
        most_constrained = max(
            self.iccs.seismograms, key=lambda s: s.begin_time - (s.t1 or s.t0)
        )
        constrained_pick = most_constrained.t1 or most_constrained.t0
        tight_window_pre = most_constrained.begin_time - constrained_pick
        valid_window_post = min(
            s.end_time - (s.t1 or s.t0) for s in self.iccs.seismograms
        )

        most_constrained.select = False

        # A window slightly beyond the constrained seismogram's edge must be rejected.
        assert (
            self.iccs.validate_time_window(
                tight_window_pre - pd.Timedelta(seconds=0.01), valid_window_post
            )
            is False
        )
        # Exactly at the boundary must be accepted.
        assert (
            self.iccs.validate_time_window(tight_window_pre, valid_window_post) is True
        )

        most_constrained.select = True

    def test_float_ramp_width_validates_correctly(self) -> None:
        """Float ramp_width must be treated as a fraction of the window duration.

        A common bug is to treat a float ramp_width as absolute seconds instead of
        as a fraction (as pysmo.functions.window does). This test verifies that with
        a large fractional ramp, a window that exactly touches the seismogram edges
        (leaving no room for the ramp) is correctly rejected.
        """
        # The tightest boundary across all seismograms (ramp=0).
        min_pre = max(s.begin_time - (s.t1 or s.t0) for s in self.iccs.seismograms)
        max_post = min(s.end_time - (s.t1 or s.t0) for s in self.iccs.seismograms)

        # Window touching seismogram edges is valid with ramp_width=0.
        assert self.iccs.validate_time_window(min_pre, max_post) is True

        # A large fractional ramp: the actual ramp will be 0.5 * window_duration > 0.
        # The same window is now rejected because the ramp extends past the edge.
        self.iccs.ramp_width = 0.5
        assert self.iccs.validate_time_window(min_pre, max_post) is False

        # The attrs validator for window_pre must also reject the edge value.
        with pytest.raises(ValueError):
            self.iccs.window_pre = min_pre

    def test_deselected_seismogram_constrains_valid_pick_range(self) -> None:
        """A deselected seismogram must still limit the valid pick delta range."""
        from pysmo.tools.iccs._iccs import _calc_valid_pick_range

        range_all_selected = _calc_valid_pick_range(self.iccs)

        most_constrained = max(
            self.iccs.seismograms, key=lambda s: s.begin_time - (s.t1 or s.t0)
        )
        most_constrained.select = False

        range_after_deselect = _calc_valid_pick_range(self.iccs)
        assert range_after_deselect[0] >= range_all_selected[0]

        most_constrained.select = True
        assert _calc_valid_pick_range(self.iccs) == range_all_selected

    def test_iccs_attribute_validation(self) -> None:
        """Test validation and cache clearing on ICCS attributes."""
        # Test validation and conversion
        self.iccs.bandpass_apply = "True"  # type: ignore
        assert self.iccs.bandpass_apply is True
        self.iccs.bandpass_fmin = "1.0"  # type: ignore
        assert self.iccs.bandpass_fmin == 1.0
        self.iccs.min_cc = "0.5"  # type: ignore
        assert self.iccs.min_cc == 0.5

        with pytest.raises(ValueError):
            self.iccs.bandpass_fmin = "abc"  # type: ignore

        # bandpass_fmin must be positive
        with pytest.raises(ValueError, match="bandpass_fmin must be positive"):
            self.iccs.bandpass_fmin = 0.0
        with pytest.raises(ValueError, match="bandpass_fmin must be positive"):
            self.iccs.bandpass_fmin = -1.0

        # bandpass_fmin must be less than bandpass_fmax
        with pytest.raises(
            ValueError, match="bandpass_fmin must be less than bandpass_fmax"
        ):
            self.iccs.bandpass_fmin = self.iccs.bandpass_fmax

        # bandpass_fmax must be greater than bandpass_fmin
        with pytest.raises(
            ValueError, match="bandpass_fmax must be greater than bandpass_fmin"
        ):
            self.iccs.bandpass_fmax = self.iccs.bandpass_fmin

        # bandpass_fmax must be below Nyquist
        nyquist = 0.5 / self.iccs.max_delta.total_seconds()
        with pytest.raises(
            ValueError, match="bandpass_fmax must be below the Nyquist frequency"
        ):
            self.iccs.bandpass_fmax = nyquist

        # Test cache clearing
        self.iccs.cc_seismograms  # Populate cache
        assert self.iccs._cc_seismograms_cache is not None
        self.iccs.min_cc = 0.4
        assert self.iccs._cc_seismograms_cache is None

        self.iccs.bandpass_apply = False
        self.iccs.cc_seismograms  # Populate cache
        assert self.iccs._cc_seismograms_cache is not None
        self.iccs.bandpass_apply = True
        assert self.iccs._cc_seismograms_cache is None

    def test_min_iccs_seismogram_validation(self) -> None:
        """Test validation on MiniIccsSeismogram attributes."""
        from pysmo.tools.iccs import MiniIccsSeismogram

        seis = self.iccs.seismograms[0]
        assert isinstance(seis, MiniIccsSeismogram)

        # flip and select are converted to bool
        seis.flip = "True"  # type: ignore
        assert seis.flip is True
        seis.select = ""  # type: ignore
        assert seis.select is False

        # data is converted to np.ndarray
        seis.data = [1, 2, 3]  # type: ignore
        assert isinstance(seis.data, np.ndarray)
        assert np.array_equal(seis.data, np.array([1, 2, 3]))

        with pytest.raises(
            ValueError,
            match=re.escape("'delta' must be > 0 days 00:00:00: -1 days +23:59:59"),
        ):
            seis.delta = pd.Timedelta(seconds=-1)

    def test_run_mccc_abs_max(self) -> None:
        """Test run_mccc with abs_max=True."""
        # Flip only one seismogram
        self.iccs.seismograms[0].data *= -1
        self.iccs.clear_cache()

        # Without abs_max=True, it should have lower absolute CC
        result_no_abs = self.iccs.run_mccc(abs_max=False)

        # With abs_max=True, it should have higher absolute CC
        result = self.iccs.run_mccc(abs_max=True)
        assert np.mean(np.abs(result.cc_means)) > np.mean(
            np.abs(result_no_abs.cc_means)
        )


class TestICCSNyquistGating:
    """Test that the Nyquist constraint on bandpass_fmax is gated by bandpass_apply."""

    def _make_coarse_seismogram(self) -> MiniIccsSeismogram:

        # delta = 1 s → Nyquist = 0.5 Hz, which is below the default bandpass_fmax = 2 Hz
        seis = MiniIccsSeismogram(
            begin_time=pd.Timestamp("2000-01-01", tz="UTC"),
            delta=pd.Timedelta(seconds=1),
            data=np.zeros(100),
            t0=pd.Timestamp("2000-01-01T00:00:30", tz="UTC"),
        )
        return seis

    def test_construction_succeeds_when_bandpass_apply_false(self) -> None:
        """ICCS(seismograms) must not raise even if default bandpass_fmax exceeds Nyquist."""
        seismograms = [self._make_coarse_seismogram() for _ in range(3)]
        iccs = ICCS(seismograms)
        assert not iccs.bandpass_apply

    def test_enabling_bandpass_apply_raises_if_fmax_exceeds_nyquist(self) -> None:
        """Switching bandpass_apply to True must raise when bandpass_fmax >= Nyquist."""
        seismograms = [self._make_coarse_seismogram() for _ in range(3)]
        iccs = ICCS(seismograms)
        with pytest.raises(
            ValueError, match="bandpass_fmax must be below the Nyquist frequency"
        ):
            iccs.bandpass_apply = True

    def test_setting_fmax_above_nyquist_allowed_when_bandpass_apply_false(
        self,
    ) -> None:
        """Setting bandpass_fmax above Nyquist is allowed while bandpass_apply is False."""
        seismograms = [self._make_coarse_seismogram() for _ in range(3)]
        iccs = ICCS(seismograms)
        nyquist = 0.5 / iccs.max_delta.total_seconds()
        iccs.bandpass_fmax = nyquist + 0.1  # should not raise

    def test_setting_fmax_at_nyquist_raises_when_bandpass_apply_true(self) -> None:
        """Setting bandpass_fmax >= Nyquist raises when bandpass_apply is True."""
        seismograms = [self._make_coarse_seismogram() for _ in range(3)]
        iccs = ICCS(seismograms)
        nyquist = 0.5 / iccs.max_delta.total_seconds()
        # First lower fmax to something valid, then enable bandpass_apply
        iccs.bandpass_fmax = nyquist * 0.5
        iccs.bandpass_apply = True  # now valid — should not raise
        with pytest.raises(
            ValueError, match="bandpass_fmax must be below the Nyquist frequency"
        ):
            iccs.bandpass_fmax = nyquist
