from tests.conftest import TESTDATA
from pysmo.tools.signal import gauss, envelope, delay
from pysmo.tools.plotseis import plotseis
from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import detrend
from pysmo.classes import SAC
import matplotlib.figure
import pytest
import pytest_cases
import numpy as np
import matplotlib
from datetime import timedelta
import random

matplotlib.use("Agg")

SACSEIS = SAC.from_file(TESTDATA["orgfile"]).seismogram
MINISEIS = MiniSeismogram(
    begin_time=SACSEIS.begin_time,
    delta=SACSEIS.delta,
    data=SACSEIS.data,
)


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
def test_envelope(seismogram: Seismogram) -> None:
    """
    Calculate gaussian envelope from Seismogram object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    env_seis = envelope(seismogram, Tn, alpha)
    assert pytest.approx(env_seis.data[100]) == 6.109130497913114


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
def test_gauss(seismogram: Seismogram) -> None:
    """
    Calculate gaussian filtered data from SacFile object and verify the calculated
    values. The reference values were obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    gauss_seis = gauss(seismogram, Tn, alpha)
    assert pytest.approx(gauss_seis.data[100]) == -5.639860165811819


@pytest.mark.depends(on=["test_envelope", "test_gauss"])
@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir="../baseline/")
def test_plot_gauss_env(seismogram: Seismogram = SACSEIS) -> matplotlib.figure.Figure:
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    seismogram.data = seismogram.data - np.mean(seismogram.data)
    gauss_seis = gauss(seismogram, Tn, alpha)
    env_seis = envelope(seismogram, Tn, alpha)
    fig = plotseis(seismogram, gauss_seis, env_seis, showfig=False)
    return fig


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
def test_delay_with_seismogram(seismogram: Seismogram) -> None:
    rand_int = int(random.uniform(10, 100))
    seismogram1 = MiniSeismogram.clone(seismogram, skip_data=True)
    seismogram1.data = seismogram.data[1000:10000]
    seismogram1 = detrend(seismogram1, clone=True)

    seismogram2 = MiniSeismogram.clone(seismogram1)
    seismogram2.delta = seismogram1.delta * 2
    with pytest.raises(ValueError):
        cc_delay, _ = delay(seismogram1, seismogram2)

    seismogram2 = MiniSeismogram.clone(seismogram1, skip_data=True)
    seismogram2.data = seismogram1.data[0:rand_int]
    with pytest.raises(ValueError):
        cc_delay, _ = delay(seismogram1, seismogram2, max_delay=timedelta(seconds=1))

    # create seismogram2 by cutting off first rand_int samples
    seismogram2 = MiniSeismogram.clone(seismogram1, skip_data=True)
    seismogram2.data = seismogram1.data[rand_int:]
    cc_delay, _ = delay(seismogram1, seismogram2)
    assert cc_delay == -rand_int * seismogram1.delta
    cc_delay, _ = delay(seismogram2, seismogram1)
    assert cc_delay == rand_int * seismogram1.delta

    # create seismogram2 by cutting off first rand_int samples and flipping polarity
    seismogram2 = MiniSeismogram.clone(seismogram1, skip_data=True)
    seismogram2.data = -seismogram1.data[rand_int:]
    cc_delay, _ = delay(seismogram1, seismogram2, allow_negative=True)
    assert cc_delay == -rand_int * seismogram1.delta
    cc_delay, _ = delay(seismogram2, seismogram1, allow_negative=True)
    assert cc_delay == rand_int * seismogram1.delta

    # create seismogram2 with a delay of rand_int * delta
    seismogram2 = MiniSeismogram.clone(seismogram1, skip_data=True)
    seismogram2.data = np.roll(seismogram1.data, rand_int)

    cc_delay, _ = delay(
        seismogram1, seismogram2, rand_int * seismogram1.delta + timedelta(seconds=2)
    )

    assert cc_delay == rand_int * seismogram1.delta

    cc_delay, _ = delay(
        seismogram2, seismogram1, rand_int * seismogram1.delta + timedelta(seconds=2)
    )

    assert cc_delay == -rand_int * seismogram1.delta


def test_delay_with_made_up_data() -> None:
    data1 = np.array([1, 1, 1, 1, 2, 3, 4, 1, 1])
    data2 = np.array([1, 1, 1, 2, 3, 4, 1])
    seismogram1 = MiniSeismogram(data=data1)
    seismogram2 = MiniSeismogram(data=data2)
    seismogram3 = MiniSeismogram(data=-data2)
    detrend(seismogram3)
    cc_delay, cc_coeff = delay(seismogram1, seismogram2)
    assert cc_delay.total_seconds() == pytest.approx(-1)
    assert cc_coeff == pytest.approx(1)
    cc_delay, cc_coeff = delay(seismogram1, seismogram3, allow_negative=True)
    assert cc_delay.total_seconds() == pytest.approx(-1)
    assert cc_coeff < 0
