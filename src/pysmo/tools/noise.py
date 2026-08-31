"""Generate realistic synthetic noise that matches the naturally observed amplitude spectrum.

Examples:
    Given the spectral amplitude in observed seismic noise on Earth is not flat
    (i.e. *not* consisting of white noise), it makes sense to calculate more
    realistic noise for things like resolution tests with synthetic data.

    In this example, random noise seismograms are generated from three different
    noise models. These are Peterson's NHNM (red), NLNM (blue), and an
    interpolated model that lies between the two (green).

    ```python exec="true" session="tools-noise-peterson"
    import matplotlib

    matplotlib.use("Agg")

    # fmt: off
    --8<-- "docs/snippets/tools/noise/peterson.py"
    # fmt: on

    from pathlib import Path

    target_dir = Path("site/images/tools/noise")
    target_dir.mkdir(parents=True, exist_ok=True)

    main(outfile=str(target_dir / "peterson.png"))
    plt.close("all")
    plt.style.use("dark_background")
    main(outfile=str(target_dir / "peterson_dark.png"))
    plt.style.use("default")

    print(
        "![peterson example](../../../images/tools/noise/peterson.png#only-light)"
        "{ loading=lazy }"
    )
    print(
        "![peterson example](../../../images/tools/noise/peterson_dark.png#only-dark)"
        "{ loading=lazy }"
    )
    ```

    ??? quote "Example source code"
        ```python title="peterson.py"
        # fmt: off
        --8<-- "docs/snippets/tools/noise/peterson.py"
        # fmt: on
        ```
"""

import warnings
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
import pandas as pd

from pysmo import MiniSeismogram
from pysmo.lib.defaults import SeismogramDefaults

__all__ = ["NoiseModel", "generate_noise", "peterson"]


@dataclass(frozen=True)
class NoiseModel:
    """Class to store seismic noise models.

    Args:
        psd: Power spectral density of ground acceleration [dB].
        T: Period.

    Examples:
        A `NoiseModel` freezes its own copy of `psd`, so the array passed in
        remains writeable and independent of the stored copy:

        ```python
        >>> import numpy as np
        >>> import pandas as pd
        >>> from pysmo.tools.noise import NoiseModel
        >>> psd = np.array([-150.0, -140.0, -130.0])
        >>> T = pd.to_timedelta([1.0, 10.0, 100.0], unit="s")
        >>> model = NoiseModel(psd=psd, T=T)
        >>> model.psd
        array([-150., -140., -130.])
        >>> psd[0] = -999.0  # does not affect the NoiseModel's own copy
        >>> model.psd[0]
        np.float64(-150.0)
        >>>
        ```
    """

    psd: npt.NDArray[np.floating] = field(
        default_factory=lambda: np.array([]),
        metadata={"description": "Power spectral density of ground acceleration [dB]."},
    )
    T: pd.TimedeltaIndex = field(
        default_factory=lambda: pd.TimedeltaIndex([]),
        metadata={"description": "Period."},
    )

    def __post_init__(self) -> None:
        """Validate `psd`/`T` have matching lengths, then freeze a copy of `psd`."""
        if np.size(self.psd) != np.size(self.T):
            raise ValueError(
                f"psd ({np.size(self.psd)}) and T ({np.size(self.T)}) arrays are not of same size"
            )
        # Freeze a copy rather than the caller's own array, so constructing a
        # NoiseModel has no side effect on the array the caller passed in.
        # T needs no equivalent treatment: unlike a plain ndarray, a
        # pd.TimedeltaIndex's underlying data is already read-only.
        psd = np.array(self.psd, copy=True)
        psd.flags.writeable = False
        object.__setattr__(self, "psd", psd)


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
    T=pd.to_timedelta(
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
        ],
        unit="s",
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
    T=pd.to_timedelta(
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
        ],
        unit="s",
    ),
)


def peterson(noise_level: float) -> NoiseModel:
    """Generate a noise model by interpolating between Peterson's[^1] New Low Noise Model (NLNM) and New High Noise Model (NHNM).

    [^1]: Peterson, Jon R. Observations and Modeling of Seismic Background
        Noise. Report, 93–322, 1993, https://doi.org/10.3133/ofr93322. USGS
        Publications Warehouse.

    Args:
        noise_level: Determines the noise level of the generated noise model.
            A noise level of 0 returns the NLNM, 1 returns the NHNM, and
            anything > 0 and < 1 returns an interpolated model that lies
            between the NLNM and NHNM.

    Returns:
        Noise model.

    Examples:
        ```python
        >>> from pysmo.tools.noise import peterson, NLNM, NHNM
        >>> peterson(0.0) == NLNM
        True
        >>> peterson(1.0) == NHNM
        True
        >>> model = peterson(0.5)
        >>> model.psd[0]  # midpoint of NLNM and NHNM at the shortest period
        np.float64(-129.75)
        >>>
        ```
    """
    # check for valid input
    if not 0 <= noise_level <= 1:
        raise ValueError(
            f"Parameter noise_level={noise_level} is not within 0-1 range."
        )

    # calculate noise model
    if noise_level == 0:
        return NLNM
    if noise_level == 1:
        return NHNM

    T_common = np.unique(
        np.concatenate((NLNM.T.total_seconds(), NHNM.T.total_seconds()))
    )
    # Peterson's model is a piecewise power law, i.e. linear in
    # log10(period), not in period itself, so interpolate in log-period
    # space to stay close to the true curve between tabulated points.
    log_T_common = np.log10(T_common)
    NLNM_interp = np.interp(log_T_common, np.log10(NLNM.T.total_seconds()), NLNM.psd)
    NHNM_interp = np.interp(log_T_common, np.log10(NHNM.T.total_seconds()), NHNM.psd)
    dB = NLNM_interp + (NHNM_interp - NLNM_interp) * noise_level
    return NoiseModel(psd=dB, T=pd.to_timedelta(T_common, unit="s"))


def generate_noise(
    model: NoiseModel,
    npts: int,
    delta: pd.Timedelta = SeismogramDefaults.delta,
    begin_time: pd.Timestamp = SeismogramDefaults.begin_time,
    return_velocity: bool = False,
    seed: int | None = None,
) -> MiniSeismogram:
    """Generate a random seismogram from a noise model.

    The amplitude spectrum is prescribed by the noise model and random phases
    are drawn uniformly from `[-π, π]`. The combined spectrum is transformed
    back to the time domain via an inverse FFT. Internally the computation is
    performed on the next power-of-two length greater than or equal to `npts`
    to ensure an efficient FFT; the central `npts` samples are then extracted
    from the result to avoid edge artefacts near the start and end of the
    generated buffer.

    Args:
        model: Noise model used to compute seismic noise.
        npts: Number of samples in the output seismogram.
        delta: Sampling interval of the generated noise.
        begin_time: Begin time of the output seismogram.
        return_velocity: If `True`, integrate the acceleration spectrum
            (division by `iω` in the frequency domain) to return ground
            velocity instead.
        seed: Random seed for reproducibility (e.g. in tests).

    Raises:
        ValueError: If `npts` is not a positive integer.

    Returns:
        Seismogram containing the generated noise. Data represent ground
        acceleration (arbitrary units matching the noise model's PSD) unless
        `return_velocity=True`, in which case they represent ground velocity.

    Examples:
        ```python
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.noise import peterson, generate_noise
        >>> model = peterson(0.0)
        >>> noise = generate_noise(
        ...     model=model, npts=64, delta=pd.Timedelta(seconds=1.0), seed=42
        ... )
        >>> isinstance(noise, MiniSeismogram)
        True
        >>> len(noise.data)
        64
        >>> noise.data[:3]
        array([-4.20418403e-09, -1.25152943e-08, -8.42501771e-09])
        >>>
        ```
    """
    if npts < 1:
        raise ValueError(f"npts={npts} must be a positive integer.")

    dt = delta.total_seconds()

    # Next power of 2 of the number of points (and at least 2, so the FFT is
    # always well defined), for an efficient FFT.
    NPTS = max(int(2 ** np.ceil(np.log2(npts))), 2)

    # Frequencies from DC to Nyquist for a real signal of length NPTS.
    freqs = np.fft.rfftfreq(NPTS, d=dt)

    # Period corresponding to each frequency; DC has no period and is handled
    # separately below (amplitude forced to zero there).
    periods = np.empty_like(freqs)
    periods[0] = np.inf
    periods[1:] = 1 / freqs[1:]

    T = model.T.total_seconds()
    if periods[1:].min() < T.min() or periods[1:].max() > T.max():
        warnings.warn(
            "Requested frequencies extend beyond the noise model's tabulated "
            + "period range; extrapolating with the nearest tabulated value.",
            stacklevel=2,
        )

    # Interpolate psd in log-period space: Peterson's model is a piecewise
    # power law, i.e. linear in log10(period), not in period itself.
    Pxx = np.interp(np.log10(periods), np.log10(T), model.psd)

    # Recreate the amplitude spectrum, with the DC term set to 0 (mean=0).
    # Pxx is a one-sided PSD (Peterson's convention, matching
    # pysmo.tools.signal.psd's scipy.signal.welch default), which doubles the
    # power of every interior bin to account for the folded negative
    # frequencies. Since only the positive-frequency half is synthesised here,
    # the target power must be halved to compensate, otherwise a one-sided
    # PSD estimate of the generated noise comes out 3 dB too high.
    amplitude = np.sqrt(10 ** (Pxx / 10) * NPTS / (2 * dt))
    amplitude[0] = 0.0

    # Phase is randomly generated; DC and Nyquist are forced real, as
    # required for a Hermitian-symmetric spectrum representing a real signal.
    rng = np.random.default_rng(seed)
    phase = (rng.random(freqs.size) - 0.5) * np.pi * 2
    phase[0] = 0.0
    phase[-1] = 0.0

    spectrum = amplitude * (np.cos(phase) + 1j * np.sin(phase))

    if return_velocity:
        # Integrate acceleration to velocity in the frequency domain
        # (division by iω), rather than the time domain: a cumulative
        # time-domain integrator is only marginally stable and introduces
        # unbounded low-frequency drift.
        omega = 2 * np.pi * freqs
        velocity_spectrum = np.zeros_like(spectrum)
        velocity_spectrum[1:] = spectrum[1:] / (1j * omega[1:])
        spectrum = velocity_spectrum

    result = np.fft.irfft(spectrum, n=NPTS)

    start = (NPTS - npts) // 2
    end = start + npts
    return MiniSeismogram(begin_time=begin_time, delta=delta, data=result[start:end])
