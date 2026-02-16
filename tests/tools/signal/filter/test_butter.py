"""Unit tests for Butterworth filter functions in _butter.py.

This module tests the bandpass, highpass, lowpass, and bandstop filter functions.
Each function is tested for both clone modes, parameter validation, and zerophase modes.
"""

from tests.test_helpers import assert_seismogram_modification
from pysmo.tools.signal._filter._butter import bandpass, highpass, lowpass, bandstop
from pysmo import Seismogram
from pytest_cases import parametrize_with_cases
from syrupy.assertion import SnapshotAssertion
import pytest
import numpy as np


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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_bandpass_invalid_freqmin(self, seismogram: Seismogram) -> None:
        """Test that bandpass raises ValueError for invalid freqmin."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmin = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmin.*is invalid for sampling rate"):
            bandpass(seismogram, freqmin=invalid_freqmin, freqmax=0.5)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_bandpass_invalid_freqmax(self, seismogram: Seismogram) -> None:
        """Test that bandpass raises ValueError for invalid freqmax."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmax = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmax.*is invalid for sampling rate"):
            bandpass(seismogram, freqmin=0.1, freqmax=invalid_freqmax)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_bandpass_freqmin_greater_than_freqmax(
        self, seismogram: Seismogram
    ) -> None:
        """Test that bandpass raises ValueError when freqmin >= freqmax."""
        with pytest.raises(ValueError, match="freqmin must be less than freqmax"):
            bandpass(seismogram, freqmin=0.5, freqmax=0.1)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_highpass_invalid_freqmin(self, seismogram: Seismogram) -> None:
        """Test that highpass raises ValueError for invalid freqmin."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmin = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmin.*is invalid for sampling rate"):
            highpass(seismogram, freqmin=invalid_freqmin)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_lowpass_invalid_freqmax(self, seismogram: Seismogram) -> None:
        """Test that lowpass raises ValueError for invalid freqmax."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmax = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmax.*is invalid for sampling rate"):
            lowpass(seismogram, freqmax=invalid_freqmax)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_bandstop_invalid_freqmin(self, seismogram: Seismogram) -> None:
        """Test that bandstop raises ValueError for invalid freqmin."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmin = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmin.*is invalid for sampling rate"):
            bandstop(seismogram, freqmin=invalid_freqmin, freqmax=0.5)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_bandstop_invalid_freqmax(self, seismogram: Seismogram) -> None:
        """Test that bandstop raises ValueError for invalid freqmax."""
        nyquist = self.get_nyquist_frequency(seismogram)
        invalid_freqmax = nyquist + 1  # Above Nyquist

        with pytest.raises(ValueError, match="freqmax.*is invalid for sampling rate"):
            bandstop(seismogram, freqmin=0.1, freqmax=invalid_freqmax)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_bandstop_freqmin_greater_than_freqmax(
        self, seismogram: Seismogram
    ) -> None:
        """Test that bandstop raises ValueError when freqmin >= freqmax."""
        with pytest.raises(ValueError, match="freqmin must be less than freqmax"):
            bandstop(seismogram, freqmin=0.5, freqmax=0.1)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
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
