import matplotlib
import matplotlib.figure
import numpy as np
import pytest
from syrupy.assertion import SnapshotAssertion

from pysmo import Seismogram
from pysmo.tools.plotutils import plotseis
from pysmo.tools.signal import envelope, gauss
from tests.test_helpers import assert_seismogram_modification

matplotlib.use("Agg")


def test_envelope(seismogram: Seismogram) -> None:
    """
    Calculate gaussian envelope from Seismogram object and verify the calculated
    values using comprehensive data validation with tolerance.
    """
    fc = 0.02  # Centre Gaussian filter at 0.02 Hz (50s period)
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    def check_envelope_properties(seis: Seismogram) -> None:
        # Verify envelope is always positive
        assert np.all(seis.data >= 0), "Envelope should be non-negative"
        # Verify envelope has reasonable values (not all zeros, not infinite)
        assert np.any(seis.data > 0), "Envelope should have positive values"
        assert np.all(np.isfinite(seis.data)), "Envelope should have finite values"

    assert_seismogram_modification(
        seismogram, envelope, fc, alpha, custom_assertions=check_envelope_properties
    )


def test_gauss(seismogram: Seismogram) -> None:
    """
    Calculate gaussian filtered data from SacFile object and verify the calculated
    values using comprehensive data validation with tolerance.
    """
    fc = 0.02  # Centre Gaussian filter at 0.02 Hz (50s period)
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    def check_gauss_properties(seis: Seismogram) -> None:
        # Verify filtered data has finite values
        assert np.all(np.isfinite(seis.data)), "Filtered data should have finite values"
        # Verify filtering doesn't create extreme outliers
        assert np.abs(np.mean(seis.data)) < 1e10, "Mean should be reasonable"

    assert_seismogram_modification(
        seismogram, gauss, fc, alpha, custom_assertions=check_gauss_properties
    )


def test_gauss_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """
    Calculate gaussian filtered data and verify against snapshot for regression testing.

    This test uses syrupy snapshots to ensure the gauss filter output remains
    consistent across code changes, helping catch unintended modifications.
    """
    fc = 0.02  # Centre Gaussian filter at 0.02 Hz (50s period)
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    assert_seismogram_modification(seismogram, gauss, fc, alpha, expected_data=snapshot)


def test_envelope_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """
    Calculate gaussian envelope and verify against snapshot for regression testing.

    This test uses syrupy snapshots to ensure the envelope output remains
    consistent across code changes, helping catch unintended modifications.
    """
    fc = 0.02  # Centre Gaussian filter at 0.02 Hz (50s period)
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    assert_seismogram_modification(
        seismogram, envelope, fc, alpha, expected_data=snapshot
    )


@pytest.mark.depends(on=["test_envelope", "test_gauss"])
@pytest.mark.mpl_image_compare(remove_text=True)
def test_plot_gauss_env(sac_seismogram: Seismogram) -> matplotlib.figure.Figure:
    """Test plotting gauss and envelope functions."""
    fc = 0.02  # Centre Gaussian filter at 0.02 Hz (50s period)
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seismogram = sac_seismogram
    seismogram.data = seismogram.data - np.mean(seismogram.data)
    gauss_seis = gauss(seismogram, fc, alpha, clone=True)
    env_seis = envelope(seismogram, fc, alpha, clone=True)
    fig = plotseis(seismogram, gauss_seis, env_seis, showfig=False)
    return fig
