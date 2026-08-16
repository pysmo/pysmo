"""Unit tests for Butterworth filter functions in _butter.py.

This module tests the bandpass, highpass, lowpass, and bandstop filter functions.
Each function is tested for both clone modes, parameter validation, and zerophase modes.
"""

import numpy as np
import pytest
from scipy.signal import iirfilter, sosfreqz
from syrupy.assertion import SnapshotAssertion

from pysmo import MiniSeismogram, Seismogram
from pysmo.tools.signal._filter._butter import (
    _zerophase_causal_ratio,
    bandpass,
    bandstop,
    causal_band,
    highpass,
    lowpass,
    zerophase_band,
)
from tests.test_helpers import assert_seismogram_modification


def test_bandpass_against_sac(
    seismogram: Seismogram, butter_seis: dict[str, MiniSeismogram]
) -> None:
    """Verify that the bandpass filter produces results consistent with SAC's implementation."""
    freqmin = 0.1
    freqmax = 0.5
    corners = 2
    zerophase = False
    bandpass(seismogram, freqmin, freqmax, corners, zerophase)
    # atol alone (as opposed to atol+rtol) would be implicitly calibrated to
    # this fixture's specific amplitude scale (counts, which vary hugely
    # between a small local event and a teleseismic M8.8) rather than
    # verifying agreement in a fixture-independent way.
    np.testing.assert_allclose(
        seismogram.data, butter_seis["butter_bandpass.sac"].data, atol=30, rtol=0.02
    )


def test_lowpass_against_sac(
    seismogram: Seismogram, butter_seis: dict[str, MiniSeismogram]
) -> None:
    """Verify that the lowpass filter produces results consistent with SAC's implementation."""
    freqmax = 0.5
    corners = 2
    zerophase = False
    lowpass(seismogram, freqmax, corners, zerophase)
    np.testing.assert_allclose(
        seismogram.data, butter_seis["butter_lowpass.sac"].data, atol=30, rtol=0.02
    )


def test_highpass_against_sac(
    seismogram: Seismogram, butter_seis: dict[str, MiniSeismogram]
) -> None:
    """Verify that the highpass filter produces results consistent with SAC's implementation."""
    freqmin = 0.1
    corners = 2
    zerophase = False
    highpass(seismogram, freqmin, corners, zerophase)
    np.testing.assert_allclose(
        seismogram.data, butter_seis["butter_highpass.sac"].data, atol=30, rtol=0.02
    )


class BaseButterFilterTest:
    """Base class for Butterworth filter tests with common assertion methods."""

    @staticmethod
    def check_filter_properties(seis: Seismogram) -> None:
        """Verify common properties of filtered data.

        Args:
            seis: The filtered seismogram to check.
        """
        # Verify filtered data has finite values
        assert np.all(np.isfinite(seis.data)), "Filtered data should have finite values"
        # Verify filtering doesn't create extreme outliers
        assert np.abs(np.mean(seis.data)) < 1e10, "Mean should be reasonable"
        # Verify data is not all zeros (filter should preserve some signal)
        assert np.any(seis.data != 0), "Filtered data should not be all zeros"

    @staticmethod
    def check_basic_properties(seis: Seismogram) -> None:
        """Verify basic properties of filtered data without mean check.

        Args:
            seis: The filtered seismogram to check.
        """
        assert np.all(np.isfinite(seis.data)), "Filtered data should have finite values"
        assert np.any(seis.data != 0), "Filtered data should not be all zeros"

    @staticmethod
    def get_nyquist_frequency(seismogram: Seismogram) -> float:
        """Calculate the Nyquist frequency for a seismogram.

        Args:
            seismogram: The seismogram to calculate Nyquist frequency for.

        Returns:
            The Nyquist frequency in Hz.
        """
        sampling_rate = 1 / seismogram.delta.total_seconds()
        return sampling_rate / 2


class TestBandpass(BaseButterFilterTest):
    """Tests for the bandpass filter function."""

    def test_bandpass(self, seismogram: Seismogram) -> None:
        """Test bandpass filter with default parameters.

        Verify that the bandpass filter correctly filters the data and that
        both clone modes produce identical results.
        """
        freqmin = 0.1  # 0.1 Hz
        freqmax = 0.5  # 0.5 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            bandpass,
            freqmin,
            freqmax,
            corners,
            custom_assertions=self.check_filter_properties,
        )

    def test_bandpass_zerophase(self, seismogram: Seismogram) -> None:
        """Test bandpass filter with zero-phase filtering.

        Zero-phase filtering applies the filter forwards and backwards to eliminate
        phase distortion.
        """
        freqmin = 0.1
        freqmax = 0.5
        corners = 2
        zerophase = True

        assert_seismogram_modification(
            seismogram,
            bandpass,
            freqmin,
            freqmax,
            corners,
            zerophase,
            custom_assertions=self.check_basic_properties,
        )

    def test_bandpass_different_corners(self, seismogram: Seismogram) -> None:
        """Test bandpass filter with different corner values.

        Higher corner values create steeper filter rolloff.
        """
        freqmin = 0.1
        freqmax = 0.5
        corners = 4  # Higher corner count

        assert_seismogram_modification(
            seismogram,
            bandpass,
            freqmin,
            freqmax,
            corners,
            custom_assertions=self.check_basic_properties,
        )

    def test_bandpass_invalid_freqmin(self, seismogram: Seismogram) -> None:
        """Test that bandpass raises ValueError for invalid freqmin."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmin = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmin.*is invalid for sampling rate"):
            bandpass(seismogram, freqmin=invalid_freqmin, freqmax=0.5)

    def test_bandpass_invalid_freqmax(self, seismogram: Seismogram) -> None:
        """Test that bandpass raises ValueError for invalid freqmax."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmax = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmax.*is invalid for sampling rate"):
            bandpass(seismogram, freqmin=0.1, freqmax=invalid_freqmax)

    def test_bandpass_freqmin_greater_than_freqmax(
        self, seismogram: Seismogram
    ) -> None:
        """Test that bandpass raises ValueError when freqmin >= freqmax."""
        with pytest.raises(ValueError, match="freqmin must be less than freqmax"):
            bandpass(seismogram, freqmin=0.5, freqmax=0.1)

    def test_bandpass_snapshot(
        self, seismogram: Seismogram, snapshot: SnapshotAssertion
    ) -> None:
        """Test bandpass filter output against snapshot for regression testing.

        Uses syrupy snapshots to ensure the bandpass filter output remains
        consistent across code changes, helping catch unintended modifications.
        """
        freqmin = 0.1  # 0.1 Hz
        freqmax = 0.5  # 0.5 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            bandpass,
            freqmin,
            freqmax,
            corners,
            expected_data=snapshot,
        )


class TestHighpass(BaseButterFilterTest):
    """Tests for the highpass filter function."""

    def test_highpass(self, seismogram: Seismogram) -> None:
        """Test highpass filter with default parameters.

        Verify that the highpass filter correctly filters the data and that
        both clone modes produce identical results.
        """
        freqmin = 0.1  # 0.1 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            highpass,
            freqmin,
            corners,
            custom_assertions=self.check_filter_properties,
        )

    def test_highpass_zerophase(self, seismogram: Seismogram) -> None:
        """Test highpass filter with zero-phase filtering."""
        freqmin = 0.1
        corners = 2
        zerophase = True

        assert_seismogram_modification(
            seismogram,
            highpass,
            freqmin,
            corners,
            zerophase,
            custom_assertions=self.check_basic_properties,
        )

    def test_highpass_different_corners(self, seismogram: Seismogram) -> None:
        """Test highpass filter with different corner values."""
        freqmin = 0.1
        corners = 4  # Higher corner count

        assert_seismogram_modification(
            seismogram,
            highpass,
            freqmin,
            corners,
            custom_assertions=self.check_basic_properties,
        )

    def test_highpass_invalid_freqmin(self, seismogram: Seismogram) -> None:
        """Test that highpass raises ValueError for invalid freqmin."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmin = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmin.*is invalid for sampling rate"):
            highpass(seismogram, freqmin=invalid_freqmin)

    def test_highpass_snapshot(
        self, seismogram: Seismogram, snapshot: SnapshotAssertion
    ) -> None:
        """Test highpass filter output against snapshot for regression testing.

        Uses syrupy snapshots to ensure the highpass filter output remains
        consistent across code changes, helping catch unintended modifications.
        """
        freqmin = 0.1  # 0.1 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            highpass,
            freqmin,
            corners,
            expected_data=snapshot,
        )


class TestLowpass(BaseButterFilterTest):
    """Tests for the lowpass filter function."""

    def test_lowpass(self, seismogram: Seismogram) -> None:
        """Test lowpass filter with default parameters.

        Verify that the lowpass filter correctly filters the data and that
        both clone modes produce identical results.
        """
        freqmax = 0.5  # 0.5 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            lowpass,
            freqmax,
            corners,
            custom_assertions=self.check_filter_properties,
        )

    def test_lowpass_zerophase(self, seismogram: Seismogram) -> None:
        """Test lowpass filter with zero-phase filtering."""
        freqmax = 0.5
        corners = 2
        zerophase = True

        assert_seismogram_modification(
            seismogram,
            lowpass,
            freqmax,
            corners,
            zerophase,
            custom_assertions=self.check_basic_properties,
        )

    def test_lowpass_different_corners(self, seismogram: Seismogram) -> None:
        """Test lowpass filter with different corner values."""
        freqmax = 0.5
        corners = 4  # Higher corner count

        assert_seismogram_modification(
            seismogram,
            lowpass,
            freqmax,
            corners,
            custom_assertions=self.check_basic_properties,
        )

    def test_lowpass_invalid_freqmax(self, seismogram: Seismogram) -> None:
        """Test that lowpass raises ValueError for invalid freqmax."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmax = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmax.*is invalid for sampling rate"):
            lowpass(seismogram, freqmax=invalid_freqmax)

    def test_lowpass_snapshot(
        self, seismogram: Seismogram, snapshot: SnapshotAssertion
    ) -> None:
        """Test lowpass filter output against snapshot for regression testing.

        Uses syrupy snapshots to ensure the lowpass filter output remains
        consistent across code changes, helping catch unintended modifications.
        """
        freqmax = 0.5  # 0.5 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            lowpass,
            freqmax,
            corners,
            expected_data=snapshot,
        )


class TestBandstop(BaseButterFilterTest):
    """Tests for the bandstop filter function."""

    def test_bandstop(self, seismogram: Seismogram) -> None:
        """Test bandstop filter with default parameters.

        Verify that the bandstop filter correctly filters the data and that
        both clone modes produce identical results.
        """
        freqmin = 0.1  # 0.1 Hz
        freqmax = 0.5  # 0.5 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            bandstop,
            freqmin,
            freqmax,
            corners,
            custom_assertions=self.check_filter_properties,
        )

    def test_bandstop_zerophase(self, seismogram: Seismogram) -> None:
        """Test bandstop filter with zero-phase filtering."""
        freqmin = 0.1
        freqmax = 0.5
        corners = 2
        zerophase = True

        assert_seismogram_modification(
            seismogram,
            bandstop,
            freqmin,
            freqmax,
            corners,
            zerophase,
            custom_assertions=self.check_basic_properties,
        )

    def test_bandstop_different_corners(self, seismogram: Seismogram) -> None:
        """Test bandstop filter with different corner values."""
        freqmin = 0.1
        freqmax = 0.5
        corners = 4  # Higher corner count

        assert_seismogram_modification(
            seismogram,
            bandstop,
            freqmin,
            freqmax,
            corners,
            custom_assertions=self.check_basic_properties,
        )

    def test_bandstop_invalid_freqmin(self, seismogram: Seismogram) -> None:
        """Test that bandstop raises ValueError for invalid freqmin."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmin = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmin.*is invalid for sampling rate"):
            bandstop(seismogram, freqmin=invalid_freqmin, freqmax=0.5)

    def test_bandstop_invalid_freqmax(self, seismogram: Seismogram) -> None:
        """Test that bandstop raises ValueError for invalid freqmax."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmax = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmax.*is invalid for sampling rate"):
            bandstop(seismogram, freqmin=0.1, freqmax=invalid_freqmax)

    def test_bandstop_freqmin_greater_than_freqmax(
        self, seismogram: Seismogram
    ) -> None:
        """Test that bandstop raises ValueError when freqmin >= freqmax."""
        with pytest.raises(ValueError, match="freqmin must be less than freqmax"):
            bandstop(seismogram, freqmin=0.5, freqmax=0.1)

    def test_bandstop_snapshot(
        self, seismogram: Seismogram, snapshot: SnapshotAssertion
    ) -> None:
        """Test bandstop filter output against snapshot for regression testing.

        Uses syrupy snapshots to ensure the bandstop filter output remains
        consistent across code changes, helping catch unintended modifications.
        """
        freqmin = 0.1  # 0.1 Hz
        freqmax = 0.5  # 0.5 Hz
        corners = 2

        assert_seismogram_modification(
            seismogram,
            bandstop,
            freqmin,
            freqmax,
            corners,
            expected_data=snapshot,
        )


def _find_3db_crossing(
    sos: np.ndarray, zerophase: bool, fs: float, edge_freq: float, margin: float = 0.6
) -> float:
    """Find a Butterworth filter's actual -3dB crossing nearest edge_freq.

    Used only by the tests below to independently verify causal_band's
    correction against a real magnitude response, rather than trusting the
    formula's own algebra.
    """
    target_db = -20 * np.log10(2**0.5)
    w, h = sosfreqz(sos, worN=200_000, fs=fs)
    mag = np.abs(h) ** 2 if zerophase else np.abs(h)
    db = 20 * np.log10(mag + 1e-300)
    mask = (w > edge_freq * (1 - margin)) & (w < edge_freq * (1 + margin))
    seg_w, seg_d = w[mask], db[mask] - target_db
    crossings = np.where(np.diff(np.sign(seg_d)) != 0)[0]
    best = crossings[np.argmin(np.abs(seg_w[crossings] - edge_freq))]
    frac = -seg_d[best] / (seg_d[best + 1] - seg_d[best])
    return float(seg_w[best] + frac * (seg_w[best + 1] - seg_w[best]))


def _residual_pct(freqmin: float, freqmax: float, corners: int, fs: float) -> float:
    """Percentage residual between the corrected-causal and zero-phase actual -3dB points at freqmax."""
    freqmin_causal, freqmax_causal = causal_band(freqmin, freqmax, corners)
    nyquist = fs / 2
    sos_zerophase = iirfilter(
        corners,
        [freqmin / nyquist, freqmax / nyquist],
        btype="band",
        ftype="butter",
        output="sos",
    )
    sos_causal_corrected = iirfilter(
        2 * corners,
        [freqmin_causal / nyquist, freqmax_causal / nyquist],
        btype="band",
        ftype="butter",
        output="sos",
    )
    zerophase_edge = _find_3db_crossing(sos_zerophase, True, fs, freqmax)
    causal_corrected_edge = _find_3db_crossing(sos_causal_corrected, False, fs, freqmax)
    return abs(causal_corrected_edge - zerophase_edge) / zerophase_edge * 100


class TestZerophaseCausalRatio:
    """Tests for _zerophase_causal_ratio."""

    def test_exact_values(self) -> None:
        """Verify the closed-form ratio at a few representative corners values."""
        assert _zerophase_causal_ratio(1) == pytest.approx(0.6435942529055827)
        assert _zerophase_causal_ratio(2) == pytest.approx(0.8022432629231502)
        assert _zerophase_causal_ratio(4) == pytest.approx(0.8956803352330285)

    def test_monotonic_increase_towards_one(self) -> None:
        """Verify the ratio increases monotonically towards 1 as corners grows."""
        ratios = [_zerophase_causal_ratio(c) for c in range(1, 33)]
        assert all(a < b for a, b in zip(ratios, ratios[1:]))
        assert ratios[-1] < 1

    @pytest.mark.parametrize("corners", [1, 2, 4, 8, 16, 32])
    def test_stays_between_zero_and_one(self, corners: int) -> None:
        """Verify the ratio is strictly inside (0, 1) for any positive corners."""
        ratio = _zerophase_causal_ratio(corners)
        assert 0 < ratio < 1


class TestCausalBand:
    """Tests for causal_band."""

    def test_edges_move_inward(self) -> None:
        """Verify freqmin moves up and freqmax moves down from the nominal band."""
        freqmin, freqmax = causal_band(0.05, 2.0, corners=2)
        assert freqmin > 0.05
        assert freqmax < 2.0

    def test_matches_ratio_composed_manually(self) -> None:
        """Verify causal_band matches _zerophase_causal_ratio composed by hand."""
        freqmin, freqmax, corners = 0.05, 2.0, 2
        ratio = _zerophase_causal_ratio(corners)
        expected = (freqmin / ratio, freqmax * ratio)
        assert causal_band(freqmin, freqmax, corners) == pytest.approx(expected)

    def test_raises_when_correction_would_invert_band(self) -> None:
        """A narrow band combined with low corners inverts the corrected band."""
        with pytest.raises(ValueError, match="would invert the band"):
            causal_band(0.5, 1.0, corners=1)

    def test_does_not_raise_on_valid_band(self) -> None:
        """The same band stays valid at a high enough corners."""
        causal_band(0.5, 1.0, corners=2)


class TestZerophaseBand:
    """Tests for zerophase_band."""

    def test_edges_move_outward(self) -> None:
        """Verify freqmin moves down and freqmax moves up from the input band."""
        freqmin, freqmax = zerophase_band(0.05, 2.0, corners=2)
        assert freqmin < 0.05
        assert freqmax > 2.0

    def test_matches_ratio_composed_manually(self) -> None:
        """Verify zerophase_band matches _zerophase_causal_ratio composed by hand."""
        freqmin, freqmax, corners = 0.05, 2.0, 2
        ratio = _zerophase_causal_ratio(corners)
        expected = (freqmin * ratio, freqmax / ratio)
        assert zerophase_band(freqmin, freqmax, corners) == pytest.approx(expected)


class TestCausalZerophaseRoundTrip:
    """Round-trip tests between causal_band and zerophase_band.

    The two directions are distinct compositions sharing the same ratio, so
    both are verified rather than treating one as implied by the other.
    """

    @pytest.mark.parametrize("corners", [1, 2, 4, 8])
    @pytest.mark.parametrize(
        "band",
        [
            (0.05, 2.0),  # IccsDefaults
            (0.5, 2.0),  # narrowband
        ],
    )
    def test_causal_then_zerophase_recovers_band(
        self, band: tuple[float, float], corners: int
    ) -> None:
        """causal_band then zerophase_band recovers the original nominal band."""
        recovered = zerophase_band(*causal_band(*band, corners), corners)
        assert recovered == pytest.approx(band)

    @pytest.mark.parametrize("corners", [1, 2, 4, 8])
    @pytest.mark.parametrize(
        "band",
        [
            (0.05, 2.0),
            (0.5, 2.0),
        ],
    )
    def test_zerophase_then_causal_recovers_band(
        self, band: tuple[float, float], corners: int
    ) -> None:
        """zerophase_band then causal_band recovers the original causal design band."""
        recovered = causal_band(*zerophase_band(*band, corners), corners)
        assert recovered == pytest.approx(band)


class TestCausalBand3dbMatching:
    """Numerical verification that causal_band's correction closes the -3dB gap
    between causal and zero-phase Butterworth bandpass filters.

    The residual is a non-negligible effect (bandpass edge interaction,
    compounded at low sample rates by Nyquist proximity), not numerical
    noise -- see `causal_band`'s own docstring for the full
    characterisation.
    """

    def test_wide_band_at_broadband_sample_rate(self) -> None:
        """A wide band at a sample rate comfortably above Nyquist gives a small residual.

        The residual here is ~1.36%; rel=0.02 covers it with margin while
        staying tight enough to catch a broken correction.
        """
        residual = _residual_pct(freqmin=0.05, freqmax=2.0, corners=2, fs=100.0)
        assert residual == pytest.approx(1.36, rel=0.2)
        assert residual < 2.0

    def test_lower_corners_same_wide_band(self) -> None:
        """Lowering corners on the same wide band grows the residual, but the correction still dominates.

        The residual is ~3.30% (vs. ~50% for the uncorrected causal filter
        at the same configuration).
        """
        residual = _residual_pct(freqmin=0.05, freqmax=2.0, corners=1, fs=100.0)
        assert residual == pytest.approx(3.30, rel=0.2)
        assert residual < 5.0

    def test_low_sample_rate_grows_residual(self) -> None:
        """A low sample rate relative to freqmax compounds a Nyquist-proximity effect onto the residual.

        The residual grows from ~1.36% (broadband) to ~2.37% at fs=20 Hz for
        the same band/corners.
        """
        residual = _residual_pct(freqmin=0.05, freqmax=2.0, corners=2, fs=20.0)
        assert residual == pytest.approx(2.37, rel=0.2)
        assert residual < 3.0
