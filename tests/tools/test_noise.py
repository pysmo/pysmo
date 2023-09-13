from dataclasses import FrozenInstanceError
from scipy import signal  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import pytest
import numpy as np
import pysmo.tools.noise as noise


def test_NoiseModel() -> None:
    # create two random arrays for testing
    psd = np.random.rand(20)
    psd2 = np.random.rand(20)
    T = np.random.rand(20)

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

    with pytest.raises(ValueError):
        model.T[3] *= 2


@pytest.mark.depends(on=["test_NoiseModel"])
@pytest.mark.mpl_image_compare(
    remove_text=True, baseline_dir="../baseline/", style="default"
)
def test_peterson():  # type: ignore
    nlnm = noise.peterson(0)
    nhnm = noise.peterson(1)
    nm_03 = noise.peterson(0.3)
    with pytest.raises(ValueError):
        noise.peterson(1.34)
    assert nlnm == noise.NLNM
    assert nhnm == noise.NHNM
    assert all(
        nm_03.T
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
    ax.plot(nlnm.T, nlnm.psd)
    ax.plot(nhnm.T, nhnm.psd)
    ax.plot(nm_03.T, nm_03.psd)
    ax.set_xscale("log")
    return fig


@pytest.mark.depends(on=["test_NoiseModel"])
@pytest.mark.mpl_image_compare(
    remove_text=True, baseline_dir="../baseline/", style="default"
)
def test_generate_noise():  # type: ignore
    npts = 10000
    nperseg = npts / 4
    nfft = npts / 2
    srate = 0.1
    sfrec = 1 / srate
    nhnm = noise.NHNM

    # velocity noise model from peterson paper
    nhnm_velo = noise.NoiseModel(
        psd=nhnm.psd + 20 * np.log10(nhnm.T / 2 / np.pi), T=nhnm.T
    )

    nhnm_data_acc = noise.generate_noise(
        model=nhnm, npts=npts, sampling_rate=srate, seed=0
    ).data
    nhnm_data_vel = noise.generate_noise(
        model=nhnm, npts=npts, sampling_rate=srate, return_velocity=True, seed=0
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
    ax1.plot(nhnm.T, nhnm.psd, "k")
    ax1.set_xscale("log")
    ax2 = fig.add_subplot(2, 1, 2)
    ax2.plot(1 / freqs_vel, 10 * np.log10(power_vel))
    ax2.plot(nhnm_velo.T, nhnm_velo.psd, "k")
    ax2.set_xscale("log")
    return fig
