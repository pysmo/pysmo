"""
Example script for pysmo.tools.noise
"""

#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
from pysmo.tools.noise import generate_noise, peterson
from pysmo.tools.signal import psd
from pandas import Timedelta


def main() -> None:
    # Set parameters
    npts: int = 200000  # multiple of 4
    delta = Timedelta(seconds=0.1)
    nperseg = int(npts / 4)
    nfft = int(npts / 2)
    time_in_seconds = np.linspace(0, npts * delta.total_seconds(), npts)

    # Calculate noise models
    low_noise_model = peterson(noise_level=0)
    mid_noise_model = peterson(noise_level=0.5)
    high_noise_model = peterson(noise_level=1)

    # Generate random noise seismograms
    low_noise_seismogram = generate_noise(npts=npts, model=low_noise_model, delta=delta)
    mid_noise_seismogram = generate_noise(npts=npts, model=mid_noise_model, delta=delta)
    high_noise_seismogram = generate_noise(
        npts=npts, model=high_noise_model, delta=delta
    )

    # Calculate power spectral density
    f_low, Pxx_dens_low = psd(low_noise_seismogram, nperseg=nperseg, nfft=nfft)
    f_mid, Pxx_dens_mid = psd(mid_noise_seismogram, nperseg=nperseg, nfft=nfft)
    f_high, Pxx_dens_high = psd(high_noise_seismogram, nperseg=nperseg, nfft=nfft)

    _ = plt.figure(figsize=(13, 9), layout="tight")

    # Plot random high and low noise seismograms
    ax1 = plt.subplot2grid((4, 3), (0, 0))
    plt.plot(time_in_seconds, high_noise_seismogram.data, "r", linewidth=0.2)
    plt.ylabel("Ground Accelaration")
    plt.xlabel("Time [s]")
    plt.xlim(time_in_seconds[0], time_in_seconds[-1])
    xticks = np.arange(
        tmin := time_in_seconds[0], (tmax := time_in_seconds[-1]) + 1, (tmax - tmin) / 5
    )
    ax1.set_xticks(xticks)

    ax2 = plt.subplot2grid((4, 3), (0, 1))
    ax2.set_xticks(xticks)
    plt.plot(time_in_seconds, mid_noise_seismogram.data, "g", linewidth=0.2)
    plt.xlabel("Time [s]")
    plt.xlim(time_in_seconds[0], time_in_seconds[-1])

    ax3 = plt.subplot2grid((4, 3), (0, 2))
    ax3.set_xticks(xticks)
    plt.plot(time_in_seconds, low_noise_seismogram.data, "b", linewidth=0.2)
    plt.xlabel("Time [s]")
    plt.xlim(time_in_seconds[0], time_in_seconds[-1])

    # Plot PSD of noise
    _ = plt.subplot2grid((4, 3), (1, 0), rowspan=3, colspan=3)
    plt.plot(
        1 / f_high,
        10 * np.log10(Pxx_dens_high),
        "r",
        linewidth=0.5,
        label="generated high noise",
    )
    plt.plot(
        1 / f_mid,
        10 * np.log10(Pxx_dens_mid),
        "g",
        linewidth=0.5,
        label="generated medium noise",
    )
    plt.plot(
        1 / f_low,
        10 * np.log10(Pxx_dens_low),
        "b",
        linewidth=0.5,
        label="generated low noise",
    )
    plt.plot(
        high_noise_model.T.total_seconds(),
        high_noise_model.psd,
        "k",
        linewidth=1,
        linestyle="dotted",
        label="NHNM",
    )
    plt.plot(
        mid_noise_model.T.total_seconds(),
        mid_noise_model.psd,
        "k",
        linewidth=1,
        linestyle="dashdot",
        label="Interpolated noise model",
    )
    plt.plot(
        low_noise_model.T.total_seconds(),
        low_noise_model.psd,
        "k",
        linewidth=1,
        linestyle="dashed",
        label="NLNM",
    )
    plt.gca().set_xscale("log")
    plt.xlim(
        low_noise_model.T.total_seconds()[0], low_noise_model.T.total_seconds()[-1]
    )
    plt.xlabel("Period [s]")
    plt.ylabel("Power Spectral Density (dB/Hz)")
    plt.legend()
    plt.savefig("peterson.png", transparent=True)
    plt.show()


if __name__ == "__main__":
    main()
