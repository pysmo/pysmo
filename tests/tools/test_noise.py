from dataclasses import FrozenInstanceError

import matplotlib.pyplot as plt  # type: ignore
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from scipy import signal  # type: ignore

import pysmo.tools.noise as noise


def test_NoiseModel() -> None:
    # create two random arrays for testing
    psd = np.random.rand(20)
    psd2 = np.random.rand(20)
    T = pd.to_timedelta(np.random.rand(20), unit="s")

    # length of the arrays needs to be equal
    with pytest.raises(ValueError):
        noise.NoiseModel(psd[1:], T)

    # create a NoiseModel instance and verify it is immutable
    model = noise.NoiseModel(psd, T)
    assert isinstance(model, noise.NoiseModel)
    with pytest.raises(FrozenInstanceError):
        model.psd = psd2  # type: ignore

    with pytest.raises(ValueError):
        model.psd[3] *= 2


@pytest.mark.mpl_image_compare(remove_text=True, style="default")
def test_peterson() -> Figure:
    nlnm = noise.peterson(0.0)
    nhnm = noise.peterson(1.0)
    nm_03 = noise.peterson(0.3)
    with pytest.raises(ValueError):
        noise.peterson(1.34)
    assert nlnm == noise.NLNM
    assert nhnm == noise.NHNM
    assert all(
        nm_03.T.total_seconds()
        == np.array(
            [
                0.10,
                0.17,
                0.22,
                0.32,
                0.40,
                0.80,
                1.24,
                2.40,
                3.80,
                4.30,
                4.60,
                5.00,
                6.00,
                6.30,
                7.90,
                10.00,
                12.00,
                15.40,
                15.60,
                20.00,
                21.90,
                31.60,
                45.00,
                70.00,
                101.00,
                154.00,
                328.00,
                354.80,
                600.00,
                10**4,
                10**5,
            ]
        )
    )
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(nlnm.T.total_seconds(), nlnm.psd)
    ax.plot(nhnm.T.total_seconds(), nhnm.psd)
    ax.plot(nm_03.T.total_seconds(), nm_03.psd)
    ax.set_xscale("log")
    return fig


def test_generate_noise_velocity_power_of_two_npts() -> None:
    """generate_noise with return_velocity=True must return exactly npts samples
    when npts is an exact power of two.

    cumulative_trapezoid reduces the internal array by 1; without the NPTS bump
    the output was silently one sample short in this case.
    """
    delta = pd.Timedelta(seconds=0.1)
    for npts in (256, 512, 1024, 2048):
        result = noise.generate_noise(
            model=noise.NHNM, npts=npts, delta=delta, return_velocity=True
        )
        assert len(result.data) == npts, (
            f"return_velocity=True with npts={npts} returned {len(result.data)} samples"
        )


def test_generate_noise_acceleration_length() -> None:
    """generate_noise without return_velocity must also return exactly npts samples
    for both power-of-two and non-power-of-two npts."""
    delta = pd.Timedelta(seconds=0.1)
    for npts in (256, 1000, 1024, 1500):
        result = noise.generate_noise(model=noise.NHNM, npts=npts, delta=delta)
        assert len(result.data) == npts


@pytest.mark.mpl_image_compare(remove_text=True, style="default")
@pytest.mark.usefixtures("seeded_noise_rng")
def test_generate_noise() -> Figure:
    npts = 10000
    nperseg = int(npts / 4)
    nfft = int(npts / 2)
    srate = 0.1
    delta = pd.Timedelta(seconds=srate)
    sfrec = 1 / srate
    nhnm = noise.NHNM

    # velocity noise model from peterson paper
    nhnm_velo = noise.NoiseModel(
        psd=(nhnm.psd + 20 * np.log10(nhnm.T.total_seconds() / 2 / np.pi)).to_numpy(),
        T=nhnm.T,
    )

    nhnm_data_acc = noise.generate_noise(model=nhnm, npts=npts, delta=delta).data
    nhnm_data_vel = noise.generate_noise(
        model=nhnm, npts=npts, delta=delta, return_velocity=True
    ).data
    freqs_acc, power_acc = signal.welch(
        nhnm_data_acc, sfrec, nperseg=nperseg, nfft=nfft, scaling="density"
    )
    freqs_vel, power_vel = signal.welch(
        nhnm_data_vel, sfrec, nperseg=nperseg, nfft=nfft, scaling="density"
    )
    freqs_acc, power_acc = freqs_acc[1:], power_acc[1:]
    freqs_vel, power_vel = freqs_vel[1:], power_vel[1:]
    fig = plt.figure()
    ax1 = fig.add_subplot(2, 1, 1)
    ax1.plot(1 / freqs_acc, 10 * np.log10(power_acc))
    ax1.plot(nhnm.T.total_seconds(), nhnm.psd, "k")
    ax1.set_xscale("log")
    ax2 = fig.add_subplot(2, 1, 2)
    ax2.plot(1 / freqs_vel, 10 * np.log10(power_vel))
    ax2.plot(nhnm_velo.T.total_seconds(), nhnm_velo.psd, "k")
    ax2.set_xscale("log")
    return fig
