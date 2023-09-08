from tests.conftest import TESTDATA
from pysmo.tools.signal import gauss, envelope
from pysmo import Seismogram, plotseis, SAC, MiniSeismogram
import matplotlib.pyplot as plt  # type: ignore
import pytest
import pytest_cases
import numpy as np
import matplotlib
matplotlib.use('Agg')

SACSEIS = SAC.from_file(TESTDATA['orgfile']).seismogram
MINISEIS = MiniSeismogram(begin_time=SACSEIS.begin_time,
                          sampling_rate=SACSEIS.sampling_rate, data=SACSEIS.data)


@pytest_cases.parametrize("seismogram",
                          (SACSEIS, MINISEIS),
                          ids=('SacSeismogram', 'MiniSeismogram'))
def test_envelope(seismogram: Seismogram) -> None:
    """
    Calculate gaussian envelope from Seismogram object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    env_seis = envelope(seismogram, Tn, alpha)
    assert pytest.approx(env_seis.data[100]) == 6.109130497913114


@pytest_cases.parametrize("seismogram",
                          (SACSEIS, MINISEIS),
                          ids=('SacSeismogram', 'MiniSeismogram'))
def test_gauss(seismogram: Seismogram) -> None:
    """
    Calculate gaussian filtered data from SacFile object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    gauss_seis = gauss(seismogram, Tn, alpha)
    assert pytest.approx(gauss_seis.data[100]) == -5.639860165811819


@pytest.mark.depends(on=['test_envelope', 'test_gauss'])
@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir='../baseline/')
def test_plot_gauss_env(seismogram: Seismogram = SACSEIS) -> plt.figure:
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seismogram.data = seismogram.data - np.mean(seismogram.data)
    gauss_seis = gauss(seismogram, Tn, alpha)
    env_seis = envelope(seismogram, Tn, alpha)
    fig = plotseis(seismogram, gauss_seis, env_seis, showfig=False)
    return fig
