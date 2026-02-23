"""Unit tests for the filter() convenience wrapper in _filter.py.

This module tests that filter() correctly dispatches to registered filter
functions, supports both clone modes, passes keyword arguments through, and
raises ValueError for unregistered filter names.
"""

import numpy as np
import pytest
from pytest_cases import parametrize_with_cases
from syrupy.assertion import SnapshotAssertion

from pysmo import Seismogram
from pysmo.tools.signal import filter
from tests.test_helpers import assert_seismogram_modification

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_invalid_name_raises(seismogram: Seismogram) -> None:
    """Test that an unregistered filter name raises ValueError."""
    with pytest.raises(ValueError, match="not registered"):
        filter(seismogram, "nonexistent_filter")  # type: ignore[call-overload]


# ---------------------------------------------------------------------------
# Butterworth filters
# ---------------------------------------------------------------------------


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_lowpass(seismogram: Seismogram) -> None:
    """Test that filter() correctly dispatches to the lowpass filter."""
    assert_seismogram_modification(
        seismogram,
        filter,
        "lowpass",
        freqmax=0.5,
        corners=2,
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_highpass(seismogram: Seismogram) -> None:
    """Test that filter() correctly dispatches to the highpass filter."""
    assert_seismogram_modification(
        seismogram,
        filter,
        "highpass",
        freqmin=0.1,
        corners=2,
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_bandpass(seismogram: Seismogram) -> None:
    """Test that filter() correctly dispatches to the bandpass filter."""
    assert_seismogram_modification(
        seismogram,
        filter,
        "bandpass",
        freqmin=0.1,
        freqmax=0.5,
        corners=2,
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_bandstop(seismogram: Seismogram) -> None:
    """Test that filter() correctly dispatches to the bandstop filter."""
    assert_seismogram_modification(
        seismogram,
        filter,
        "bandstop",
        freqmin=0.1,
        freqmax=0.5,
        corners=2,
    )


# ---------------------------------------------------------------------------
# Gaussian filters
# ---------------------------------------------------------------------------


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_gauss(seismogram: Seismogram) -> None:
    """Test that filter() correctly dispatches to the gauss filter."""

    def check_gauss_properties(seis: Seismogram) -> None:
        assert np.all(np.isfinite(seis.data)), "Filtered data should have finite values"

    assert_seismogram_modification(
        seismogram,
        filter,
        "gauss",
        Tn=50,
        alpha=50,
        custom_assertions=check_gauss_properties,
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_envelope(seismogram: Seismogram) -> None:
    """Test that filter() correctly dispatches to the envelope filter."""

    def check_envelope_properties(seis: Seismogram) -> None:
        assert np.all(seis.data >= 0), "Envelope should be non-negative"
        assert np.all(np.isfinite(seis.data)), "Envelope should have finite values"

    assert_seismogram_modification(
        seismogram,
        filter,
        "envelope",
        Tn=50,
        alpha=50,
        custom_assertions=check_envelope_properties,
    )


# ---------------------------------------------------------------------------
# Snapshot regression tests
# ---------------------------------------------------------------------------


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_filter_bandpass_snapshot(
    seismogram: Seismogram, snapshot: SnapshotAssertion
) -> None:
    """Test filter() bandpass output against snapshot for regression testing."""
    assert_seismogram_modification(
        seismogram,
        filter,
        "bandpass",
        freqmin=0.1,
        freqmax=0.5,
        corners=2,
        expected_data=snapshot,
    )
