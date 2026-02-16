from tests.test_helpers import assert_seismogram_modification
from pysmo.tools.signal import gauss, envelope
from pysmo.tools.plotutils import plotseis
from pysmo import Seismogram
from pytest_cases import parametrize_with_cases
import pytest
import matplotlib.figure
import matplotlib
import numpy as np

matplotlib.use("Agg")


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_envelope(seismogram: Seismogram, snapshot) -> None:
    """
    Calculate gaussian envelope from Seismogram object and verify the calculated
    values using snapshot testing for comprehensive data validation.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    assert_seismogram_modification(seismogram, envelope, Tn, alpha, snapshot=snapshot)


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_gauss(seismogram: Seismogram, snapshot) -> None:
    """
    Calculate gaussian filtered data from SacFile object and verify the calculated
    values using snapshot testing for comprehensive data validation.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    assert_seismogram_modification(seismogram, gauss, Tn, alpha, snapshot=snapshot)


@pytest.mark.depends(on=["test_envelope", "test_gauss"])
@pytest.mark.mpl_image_compare(remove_text=True)
def test_plot_gauss_env(sac_seismogram: Seismogram) -> matplotlib.figure.Figure:
    """Test plotting gauss and envelope functions."""
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seismogram = sac_seismogram
    seismogram.data = seismogram.data - np.mean(seismogram.data)
    gauss_seis = gauss(seismogram, Tn, alpha, clone=True)
    env_seis = envelope(seismogram, Tn, alpha, clone=True)
    fig = plotseis(seismogram, gauss_seis, env_seis, showfig=False)
    return fig
