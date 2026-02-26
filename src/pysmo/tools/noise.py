"""
Generate realistic synthetic noise.


matches the naturally observed amplitude spectrum.

Examples:
    Given the spectral amplitude in observed seismic noise on Earth is not flat
    (i.e. *not* consisting of white noise), it makes sense to calculate more
    realistic noise for things like resolution tests with synthetic data.

    In this example, random noise seismograms are generated from three different
    noise models. These are Peterson's NHNM (red), NLNM (blue), and an
    interpolated model that lies between the two (green).

    ![peterson example](../../../images/tools/noise/peterson.png#only-light){ loading=lazy }
    ![peterson example](../../../images/tools/noise/peterson_dark.png#only-dark){ loading=lazy }

    ??? quote "Example source code"
        ```python title="peterson.py"
        --8<-- "docs/snippets/tools/noise/peterson.py"
        ```
"""

import numpy as np
from pandas import Timestamp, Timedelta
from dataclasses import dataclass, field
from scipy.integrate import cumulative_trapezoid
from pysmo import MiniSeismogram
from pysmo.lib.defaults import SeismogramDefaults

__all__ = ["NoiseModel", "peterson", "generate_noise"]


@dataclass(frozen=True)
class NoiseModel:
    """Class to store seismic noise models.

    Parameters:
        psd: Power spectral density of ground acceleration [dB].
        T: Period [seconds].
    """

    psd: np.ndarray = field(
        default_factory=lambda: np.array([]),
        metadata={"description": "Power spectral density of ground acceleration [dB]."},
    )
    T: np.ndarray = field(
        default_factory=lambda: np.array([]),
        metadata={"description": "Period [seconds]."},
    )

    def __post_init__(self) -> None:
        if np.size(self.psd) != np.size(self.T):
            raise ValueError(
                "dB and T arrays are not of same size",
                f"({np.size(self.psd)} != {np.size(self.T)}",
            )
        self.psd.flags.writeable = False
        self.T.flags.writeable = False


NLNM = NoiseModel(
    psd=np.array(
        [
            -168.0,
            -166.7,
            -166.7,
            -169.2,
            -163.7,
            -148.6,
            -141.1,
            -141.1,
            -149.0,
            -163.8,
            -166.2,
            -162.1,
            -177.5,
            -185.0,
            -187.5,
            -187.5,
            -185.0,
            -185.0,
            -187.5,
            -184.4,
            -151.9,
            -103.1,
        ]
    ),
    T=np.array(
        [
            0.10,
            0.17,
            0.40,
            0.80,
            1.24,
            2.40,
            4.30,
            5.00,
            6.00,
            10.00,
            12.00,
            15.60,
            21.90,
            31.60,
            45.00,
            70.00,
            101.00,
            154.00,
            328.00,
            600.00,
            10**4,
            10**5,
        ]
    ),
)

NHNM = NoiseModel(
    psd=np.array(
        [
            -91.5,
            -97.4,
            -110.5,
            -120.0,
            -98.0,
            -96.5,
            -101.0,
            -113.5,
            -120.0,
            -138.5,
            -126.0,
            -80.1,
            -48.5,
        ]
    ),
    T=np.array(
        [
            0.10,
            0.22,
            0.32,
            0.80,
            3.80,
            4.60,
            6.30,
            7.90,
            15.40,
            20.00,
            354.80,
            10**4,
            10**5,
        ]
    ),
)


def peterson(noise_level: float) -> NoiseModel:
    """Generate a noise model by interpolating between Peterson's[^1]
    New Low Noise Model (NLNM) and New High Noice Model (NHNM).

    [^1]: Peterson, Jon R. Observations and Modeling of Seismic Background
        Noise. Report, 93–322, 1993, https://doi.org/10.3133/ofr93322. USGS
        Publications Warehouse.

    Args:
        noise_level: Determines the noise level of the generated noise model.
                     A noise level of 0 returns the NLNM, 1 returns the NHNM,
                     and anything > 0 and < 1 returns an interpolated model
                     that lies between the NLNM and NHNM.

    Returns:
        Noise model.
    """
    # check for valid input
    if not 0 <= noise_level <= 1:
        raise ValueError(
            f"Parameter noise_level={noise_level} is not within 0-1 range."
        )

    # calculate noise model
    if noise_level == 0:
        return NLNM
    elif noise_level == 1:
        return NHNM
    else:
        T_common = np.unique(np.concatenate((NLNM.T, NHNM.T)))
        NLNM_interp = np.interp(T_common, NLNM.T, NLNM.psd)
        NHNM_interp = np.interp(T_common, NHNM.T, NHNM.psd)
        dB = NLNM_interp + (NHNM_interp - NLNM_interp) * noise_level
        return NoiseModel(psd=dB, T=T_common)


def generate_noise(
    model: NoiseModel,
    npts: int,
    delta: Timedelta = SeismogramDefaults.delta,
    begin_time: Timestamp = SeismogramDefaults.begin_time,
    return_velocity: bool = False,
    seed: int | None = None,
) -> MiniSeismogram:
    """Generate a random seismogram from a noise model. Realistic seismic noise is
    generated by assigning random phases to a fixed amplitude spectrum prescribed by a
    noise model.

    Args:
        model: Noise model used to compute seismic noise.
        npts: Number of points of generated noise
        delta: Sampling interval of generated noise
        begin_time: Seismogram begin time
        return_velocity: Return velocity instead of acceleration.
        seed: set random seed manually (usually for testing purposes).

    Returns:
        Seismogram with random seismic noise as data.
    """
    # Sampling frequency
    Fs = 1 / delta.total_seconds()

    # Nyquist frequency
    Fnyq = 0.5 / delta.total_seconds()

    # get next power of 2 of the nunmber of points and calculate frequencies from
    # Fs/NPTS to Fnyq (we skip a frequency of 0 for now to avoid dividing by 0)
    NPTS = int(2 ** np.ceil(np.log2(npts)))
    freqs = np.linspace(Fs / NPTS, Fnyq, NPTS - 1)

    # interpolate psd and recreate amplitude spectrum with the first
    # term=0 (i.e. mean=0).
    Pxx = np.interp(1 / freqs, model.T, model.psd)
    spectrum = np.append(
        np.array([0]), np.sqrt(10 ** (Pxx / 10) * NPTS / delta.total_seconds() * 2)
    )

    # phase is randomly generated
    rng = np.random.default_rng(seed)
    phase = (rng.random(NPTS) - 0.5) * np.pi * 2

    # combine amplitude with phase and perform ifft
    NewX = spectrum * (np.cos(phase) + 1j * np.sin(phase))
    acceleration = np.fft.irfft(NewX)

    start = int((NPTS - npts) / 2)
    end = start + npts
    if return_velocity:
        velocity = cumulative_trapezoid(acceleration, dx=delta.total_seconds())
        velocity = velocity[start:end]
        return MiniSeismogram(begin_time=begin_time, delta=delta, data=velocity)
    acceleration = acceleration[start:end]
    return MiniSeismogram(begin_time=begin_time, delta=delta, data=acceleration)
