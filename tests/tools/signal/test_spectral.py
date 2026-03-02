"""Unit tests for spectral analysis functions in _spectral.py."""

import numpy as np
from pytest_cases import parametrize_with_cases
from syrupy.assertion import SnapshotAssertion

from pysmo import Seismogram
from pysmo.tools.signal import psd


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_psd_basic(seismogram: Seismogram) -> None:
    """Test basic functionality of the psd function.

    Verifies that it returns two numpy arrays of correct and equal length,
    and that the first frequency is greater than zero (f=0Hz dropped).
    """
    npts = len(seismogram.data)
    nperseg = npts // 4
    nfft = npts // 2

    freqs, psd_values = psd(seismogram, nperseg=nperseg, nfft=nfft)

    assert isinstance(freqs, np.ndarray)
    assert isinstance(psd_values, np.ndarray)
    assert len(freqs) == len(psd_values)
    assert freqs[0] > 0  # f=0Hz should be dropped


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_psd_parameters(seismogram: Seismogram) -> None:
    """Test psd function with different parameters.

    Verifies that nperseg and nfft affect the output length as expected
    by scipy.signal.welch.
    """
    npts = len(seismogram.data)

    # Test different nperseg/nfft
    nperseg1, nfft1 = npts // 8, npts // 4
    freqs1, psd1 = psd(seismogram, nperseg=nperseg1, nfft=nfft1)

    nperseg2, nfft2 = npts // 4, npts // 2
    freqs2, psd2 = psd(seismogram, nperseg=nperseg2, nfft=nfft2)

    assert len(freqs1) != len(freqs2)
    # nfft determines number of frequency bins.
    # For real input, it returns nfft//2 + 1.
    # We drop f=0, so expected length is nfft//2.
    assert len(freqs1) == nfft1 // 2
    assert len(freqs2) == nfft2 // 2


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_psd_scaling(seismogram: Seismogram) -> None:
    """Test psd function with different scaling options."""
    npts = len(seismogram.data)
    nperseg = npts // 4
    nfft = npts // 2

    freqs_dens, psd_dens = psd(
        seismogram, nperseg=nperseg, nfft=nfft, scaling="density"
    )
    freqs_spec, psd_spec = psd(
        seismogram, nperseg=nperseg, nfft=nfft, scaling="spectrum"
    )

    assert np.allclose(freqs_dens, freqs_spec)
    assert not np.allclose(psd_dens, psd_spec)


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_psd_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """Test psd output against snapshot for regression testing."""
    # Use fixed parameters for stable snapshots
    # Seismogram cases have 180000 points
    nperseg = 1000
    nfft = 2000

    freqs, psd_values = psd(seismogram, nperseg=nperseg, nfft=nfft)

    # Combined snapshot of freqs and psd
    assert (freqs, psd_values) == snapshot
