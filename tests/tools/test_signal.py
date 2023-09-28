from tests.conftest import TESTDATA
from pysmo.tools.signal import gauss, envelope, xcorr
from pysmo import Seismogram, plotseis, SAC, MiniSeismogram
import matplotlib.pyplot as plt  # type: ignore
import pytest
import pytest_cases
import numpy as np
import matplotlib

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
def test_plot_gauss_env(seismogram: Seismogram = SACSEIS) -> plt.figure:
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
def test_xcorr(seismogram: Seismogram) -> None:
    duration = 100  # seconds
    delta = 0.025  # x-axis step
    xbase = np.arange(0, duration, delta)
    noise = np.random.default_rng(seed=42).normal(0, 0.2, len(xbase))
    a = (
        np.exp(-0.5 * ((xbase - 12) / 1) ** 2)
        - 0.3 * np.exp(-0.5 * ((xbase - 16) / 1) ** 2)
        + noise
    )
    lag_times = [10, 12.5, 17]

    for testcase in range(3):
        if testcase == 0:
            x = xbase
            v = np.exp(-0.5 * ((x - 18) / 1) ** 2)
            expected_arr = [
                0.039453,
                0.040382,
                0.041337,
                0.042319,
                0.043331,
                0.044373,
                0.045447,
                0.046555,
                0.047698,
                0.048879,
            ]

        if testcase == 1:
            ind = round(len(xbase) / 8)
            x = xbase[ind:-ind]
            v = np.exp(-0.5 * ((x - 18) / 1) ** 2)
            expected_arr = [
                -0.006293,
                -0.006286,
                -0.006272,
                -0.006248,
                -0.006215,
                -0.006173,
                -0.006121,
                -0.006059,
                -0.005986,
                -0.005902,
            ]

        if testcase == 2:
            x = np.arange(-17, duration + 17, delta)
            v = np.exp(-0.5 * ((x - 18) / 1) ** 2)
            expected_arr = [
                -0.002352,
                -0.002758,
                -0.003177,
                -0.003607,
                -0.004049,
                -0.004502,
                -0.004965,
                -0.005439,
                -0.005922,
                -0.006414,
            ]

        seis1 = MiniSeismogram(data=a, delta=delta)
        seis2 = MiniSeismogram(data=v, delta=delta)
        corr_arr = xcorr(seis1, seis2, lag_times[testcase])

        assert np.allclose(np.round(corr_arr[:10], decimals=6), np.array(expected_arr))

    # Test on sac files
    lag = 20
    shift = int(lag / seismogram.delta)
    seismogram_lagged = MiniSeismogram.clone(seismogram, skip_data=True)
    seismogram_lagged.data = np.roll(seismogram.data, shift)
    corr_arr = xcorr(seismogram, seismogram_lagged, lag)
    expected_arr = [
        0.99999994,
        0.9998093,
        0.9995737,
        0.9994081,
        0.999202,
        0.9990382,
        0.99889684,
        0.99881154,
        0.99875396,
        0.99869645,
    ]

    assert np.allclose(np.round(corr_arr[:10], decimals=6), np.array(expected_arr))
