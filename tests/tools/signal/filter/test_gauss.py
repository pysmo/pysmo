from tests.conftest import TESTDATA
from tests.test_helpers import assert_seismogram_modification
from pysmo.tools.signal import gauss, envelope
from pysmo.tools.plotutils import plotseis
from pysmo import Seismogram, MiniSeismogram
from pysmo.classes import SAC
from pytest_cases import parametrize_with_cases
import pytest
import matplotlib.figure
import matplotlib
import numpy as np

matplotlib.use("Agg")


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_envelope(seismogram: Seismogram) -> None:
    """
    Calculate gaussian envelope from Seismogram object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    def check_envelope(seis: Seismogram) -> None:
        assert pytest.approx(seis.data[100]) == 6.109130497913114

    assert_seismogram_modification(
        seismogram, envelope, Tn, alpha, custom_assertions=check_envelope
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_gauss(seismogram: Seismogram) -> None:
    """
    Calculate gaussian filtered data from SacFile object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50

    def check_gauss(seis: Seismogram) -> None:
        assert pytest.approx(seis.data[100]) == -5.639860165811819

    assert_seismogram_modification(
        seismogram, gauss, Tn, alpha, custom_assertions=check_gauss
    )


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
