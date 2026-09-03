"""Generate synthetic noise from Peterson's noise models and check it.

A random seismogram is generated from each of Peterson's New Low Noise Model
(NLNM), New High Noise Model (NHNM), and an interpolated model half way
between them. The power spectral density of every generated seismogram is
plotted on top of the model it was drawn from, showing that ``generate_noise``
reproduces the target spectrum.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pysmo.tools.noise import generate_noise, peterson
from pysmo.tools.signal import psd

# name, Peterson noise level, plot colour, model label, model line style
NOISE_LEVELS = [
    ("low", 0.0, "b", "NLNM", "dashed"),
    ("mid", 0.5, "g", "interpolated model", "dashdot"),
    ("high", 1.0, "r", "NHNM", "dotted"),
]


def main(outfile: str = "peterson.png") -> None:
    # A long series gives the PSD estimate enough frequency resolution to
    # track the model curves; npts must be a multiple of 4 for the Welch
    # segment and FFT lengths below.
    npts = 200_000
    delta = pd.Timedelta(seconds=0.1)
    nperseg, nfft = npts // 4, npts // 2
    times = np.linspace(0.0, npts * delta.total_seconds(), npts)

    fig, axes = plt.subplot_mosaic(
        [
            ["low", "mid", "high"],
            ["psd", "psd", "psd"],
            ["psd", "psd", "psd"],
            ["psd", "psd", "psd"],
        ],
        figsize=(13, 9),
        layout="tight",
    )
    psd_ax = axes["psd"]

    for name, level, color, model_label, model_style in NOISE_LEVELS:
        model = peterson(noise_level=level)
        seismogram = generate_noise(npts=npts, model=model, delta=delta)
        freqs, power = psd(seismogram, nperseg=nperseg, nfft=nfft)

        wave_ax = axes[name]
        wave_ax.plot(times, seismogram.data, color, linewidth=0.2)
        wave_ax.set_xlim(times[0], times[-1])
        wave_ax.set_xlabel("Time [s]")
        wave_ax.locator_params(axis="x", nbins=4)

        # Skip the zero-frequency bin before converting to period.
        psd_ax.plot(
            1 / freqs[1:],
            10 * np.log10(power[1:]),
            color,
            linewidth=0.5,
            label=f"generated {name} noise",
        )
        psd_ax.plot(
            model.T.total_seconds(),
            model.psd,
            color=plt.rcParams["text.color"],  # legible in light and dark themes
            linewidth=1,
            linestyle=model_style,
            label=model_label,
        )

    axes["low"].set_ylabel("Ground acceleration")

    periods = peterson(0.0).T.total_seconds()
    psd_ax.set_xscale("log")
    psd_ax.set_xlim(periods[0], periods[-1])
    psd_ax.set_xlabel("Period [s]")
    psd_ax.set_ylabel("Power spectral density [dB]")
    psd_ax.legend()

    fig.savefig(outfile, transparent=True)
    plt.show()


if __name__ == "__main__":
    main()
