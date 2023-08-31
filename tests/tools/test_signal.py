"""Run tests for all functions defined in pysmo.tools.noise"""

from pysmo import Seismogram
from pysmo.functions import plotseis
from pysmo.tools.signal import gauss, envelope
import matplotlib.pyplot as plt  # type: ignore
import pytest
import numpy as np
import matplotlib
matplotlib.use('Agg')


def test_envelope(seismograms: tuple[Seismogram, ...]) -> None:
    """
    Calculate gaussian envelope from Seismogram object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    for seis in seismograms:
        env_seis = envelope(seis, Tn, alpha)
        assert pytest.approx(env_seis.data[100]) == 6.109130497913114


def test_gauss(seismograms: tuple[Seismogram, ...]) -> None:
    """
    Calculate gaussian filtered data from SacFile object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    for seis in seismograms:
        gauss_seis = gauss(seis, Tn, alpha)
        assert pytest.approx(gauss_seis.data[100]) == -5.639860165811819


@pytest.mark.depends(on=['test_envelope', 'test_gauss'])
@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir='../baseline/')
def test_plot_gauss_env(seismograms: tuple[Seismogram, ...]) -> plt.figure:
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seis, *_ = seismograms
    seis.data = seis.data - np.mean(seis.data)
    seis.label = "Unfiltered"  # type: ignore
    gauss_seis = gauss(seis, Tn, alpha)
    gauss_seis.label = "Gaussian filtered"  # type: ignore
    env_seis = envelope(seis, Tn, alpha)
    env_seis.label = "Envelope"  # type: ignore
    fig = plotseis(seis, gauss_seis, env_seis, showfig=False)
    return fig
