"""Instrument response removal."""

import warnings
from copy import deepcopy
from typing import Literal, overload

import numpy as np
import scipy.signal

from pysmo import Response, Seismogram, StagedResponse

__all__ = ["remove_response"]


def _analog_transfer_function(response: Response, freqs: np.ndarray) -> np.ndarray:
    """Evaluate the analog (poles/zeros) transfer function at `freqs` (Hz)."""
    s = 1j * 2 * np.pi * freqs
    zeros = np.asarray(response.zeros, dtype=complex)
    poles = np.asarray(response.poles, dtype=complex)
    numerator = np.prod(s[:, None] - zeros[None, :], axis=1)
    denominator = np.prod(s[:, None] - poles[None, :], axis=1)
    return response.overall_sensitivity * numerator / denominator


def _digital_transfer_function(
    response: StagedResponse, freqs: np.ndarray
) -> np.ndarray:
    """Evaluate the combined digital-stage transfer function at `freqs` (Hz)."""
    result = np.ones_like(freqs, dtype=complex)
    for stage in response.stages:
        _, h = scipy.signal.freqz(
            stage.numerator, stage.denominator, worN=freqs, fs=stage.input_sample_rate
        )
        if stage.correction:
            # freqz reproduces the filter's own, uncorrected delay; the
            # recorded data has already had `correction` seconds of that
            # delay removed (see ResponseStage.correction), so cancel the
            # same amount here to match what was actually recorded.
            h = h * np.exp(2j * np.pi * freqs * stage.correction)
        result *= h
    return result


def _pre_filt_taper(
    freqs: np.ndarray, pre_filt: tuple[float, float, float, float]
) -> np.ndarray:
    r"""Build a four-corner cosine taper ($f_1 < f_2 \le f_3 < f_4$) over `freqs`."""
    f1, f2, f3, f4 = pre_filt
    taper = np.zeros_like(freqs)

    ramp_up = (freqs >= f1) & (freqs < f2)
    taper[ramp_up] = 0.5 * (1 - np.cos(np.pi * (freqs[ramp_up] - f1) / (f2 - f1)))

    flat = (freqs >= f2) & (freqs <= f3)
    taper[flat] = 1.0

    ramp_down = (freqs > f3) & (freqs <= f4)
    taper[ramp_down] = 0.5 * (1 + np.cos(np.pi * (freqs[ramp_down] - f3) / (f4 - f3)))

    return taper


@overload
def remove_response(
    seismogram: Seismogram,
    response: Response,
    pre_filt: tuple[float, float, float, float] | None = ...,
    *,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def remove_response[T: Seismogram](
    seismogram: T,
    response: Response,
    pre_filt: tuple[float, float, float, float] | None = ...,
    *,
    clone: Literal[True],
) -> T: ...


def remove_response[T: Seismogram](
    seismogram: T,
    response: Response,
    pre_filt: tuple[float, float, float, float] | None = None,
    *,
    clone: bool = False,
) -> T | None:
    r"""Remove an instrument response from a seismogram.

    Two modes are available, chosen by whether `pre_filt` is given:

    **`pre_filt=None` (default) — sensitivity-only division.** Divides
    `seismogram.data` by `response.reference_sensitivity` alone, in the time
    domain. No FFT, no frequency-dependent correction: this is only correct
    where the true instrument response is flat with $\approx 0$ phase, i.e. within
    the sensor's own passband, and is appropriate when the signal of interest
    is confined to that flat band (the common case for a well-chosen broadband
    instrument). It will *not* correct roll-off near the sensor's corner
    frequencies or any digital decimation stages; for that, use `pre_filt`.
    Note this divides by `reference_sensitivity`, not `overall_sensitivity` —
    the latter has the analog stage's $A_0$ normalisation factor folded in (see
    [`Response.overall_sensitivity`][pysmo.Response.overall_sensitivity]).

    For a [`SacPZ`][pysmo.classes.SacPZ]-derived `response`, this path's output
    is typically *not* in the units `input_units` declares: by SAC convention
    (followed by e.g. the EarthScope SACPZ web service and `rdseed -p`), the
    `SENSITIVITY` header (`reference_sensitivity`) stays in the sensor's
    native units (e.g. `M/S**2` for an accelerometer), while
    `poles`/`zeros`/`overall_sensitivity` — and therefore `input_units`, and
    the full-deconvolution path below — are normalised to displacement. This
    is a convention of the *producer*, not something `SacPZ`/`parse_sacpz`
    enforce or verify — a hand-written SAC PZ file that doesn't follow it will
    not exhibit this split. A [`StationXML`][pysmo.classes.StationXML]-derived
    `response` has no such split: both paths agree with `input_units`.

    **`pre_filt` given — spectral deconvolution.** Deconvolves `seismogram.data`
    by the instrument response's full complex transfer function $H(f)$,
    applying a four-corner cosine taper $\text{taper}(f)$:

    $$Y(f) = X(f) \cdot \frac{\text{taper}(f)}{H(f)}$$

    The effective filter response $\frac{\text{taper}(f)}{H(f)}$ is forced to
    zero outside $(f_1, f_4)$ (skipping division by $H(f)$ where $\text{taper}(f) = 0$),
    and cosine-tapered at the edges ($f_1 < f_2 \le f_3 < f_4$, in Hz), so frequencies
    excluded from the passband are never amplified. There is no additional
    stabilisation: if $H(f)$ is zero or very small at a frequency inside
    $(f_1, f_4)$, division amplifies noise without limit, and an exact zero
    produces non-finite values ($\infty$ or $\text{NaN}$) that poison the entire
    output once inverse-transformed. Consequently, $f_1$ must remain strictly
    above 0 Hz, since velocity- and acceleration-output sensors have a zero at DC
    by construction (2 or 3 zeros at the origin, respectively — that is what makes
    it a velocity/acceleration sensor, not a displacement one).

    The right bound for $f_4$ also depends on whether `response` actually carries
    digital FIR/IIR decimation stages — not just whether it satisfies
    [`StagedResponse`][pysmo.StagedResponse], since e.g.
    [`StationXML.response`][pysmo.classes.StationXML.response] always satisfies that protocol but its
    `stages` is empty for a document with no digital stage on record:

    - **No digital stages** (`stages` empty, e.g. a SAC PZ-derived response, or a
      StationXML document without one): only the analog poles/zeros/sensitivity go
      into $H(f)$. Pushing $f_4$ above roughly 80% of the seismogram's own Nyquist
      frequency triggers the `UserWarning` described below — the analog-only
      approximation ignores the roll-off and phase a real digitiser's decimation
      filter would otherwise contribute near its own Nyquist.
    - **Digital stages present** (`stages` non-empty): they are folded into $H(f)$
      too, so $f_4$ should also stay clear of their own cutoff — bound it by the
      stages' own Nyquist (half their `input_sample_rate`), not just the
      seismogram's, since a stage's own zeros cluster in its stopband near/above
      that frequency. Stages are also assumed to have had their own filter delay
      already corrected out of the recorded data (`ResponseStage.correction`,
      matching FDSN StationXML's `Decimation/Correction`, as is standard for
      archived data) — if that assumption doesn't hold for a given `response`,
      the deconvolved output will carry a spurious time shift equal to that
      correction.

    No other preprocessing is performed in the deconvolution path:
    `seismogram.data` is not zero-padded, demeaned, detrended, or tapered in
    the time domain before the FFT. Since `rfft`/`irfft` implicitly treat
    the data as one period of a periodic signal, an uncorrected mean/trend
    or an abrupt jump between the segment's start and end will produce
    wraparound artefacts in the deconvolved output rather than being cleanly
    removed. Detrend and taper the seismogram first (e.g. with
    [`pysmo.functions.detrend`][] and
    [`pysmo.functions.taper`][]), as is standard
    practice before any FFT-based deconvolution.

    Args:
        seismogram: The seismogram to deconvolve.
        response: The instrument response to remove. Output is in whatever
            physical units `response.input_units` declares; no unit
            conversion is performed (see
            [`integrate`][pysmo.tools.signal.integrate]/
            [`differentiate`][pysmo.tools.signal.differentiate] to convert
            between displacement/velocity/acceleration afterwards).
        pre_filt: Optional four corner frequencies $(f_1, f_2, f_3, f_4)$ in Hz
            defining a cosine taper applied before division: zero below
            $f_1$, cosine ramp up to $f_2$, flat through $[f_2, f_3]$, cosine
            ramp down to $f_4$, zero above $f_4$. `None` (the default) skips
            spectral deconvolution entirely and instead divides by
            `response.reference_sensitivity` in the time domain — see above.
            Not derived automatically — see Examples for how to choose a
            starting point.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Processed [`Seismogram`][pysmo.Seismogram] object if called with
        `clone=True`.

    Raises:
        ValueError: If `seismogram.data` is empty; if `pre_filt` is `None`
            and `response.reference_sensitivity` is also `None`; or, when
            `pre_filt` is given, if `seismogram.delta` is not positive, its
            lower corner $f_1$ is not above 0, its corners are not strictly
            increasing ($f_1 < f_2 \le f_3 < f_4$), or its upper corner
            exceeds the seismogram's Nyquist frequency.

    Warns:
        UserWarning: If `pre_filt` is given and `response`'s `stages` is
            empty (whether because it does not satisfy
            [`StagedResponse`][pysmo.StagedResponse] at all, as is always
            the case for a response parsed from a SAC PZ file, or because it
            does but has no digital stage on record) and `pre_filt`'s upper
            corner is above a conservative 80% of the seismogram's own
            Nyquist frequency (a heuristic margin, not a precise bound) —
            the analog-only approximation gets progressively less accurate
            towards Nyquist, where a real digitiser's decimation filter
            would otherwise contribute roll-off and phase. Or, if `stages`
            is non-empty and `pre_filt`'s upper corner is above 80% of the
            slowest stage's own Nyquist frequency (half its
            `input_sample_rate`) — beyond that point `scipy.signal.freqz`
            wraps around and returns an aliased value for that stage instead
            of its actual roll-off.

    Examples:
        The examples below build on the same setup: `example.sac`'s own real
        response — a broadband seismometer and digitiser, from a genuine StationXML
        document for the actual station and epoch that recorded it.

        Sensitivity-only division:

        ```python
        >>> from pathlib import Path
        >>> from pysmo.classes import SAC, StationXML
        >>> from pysmo.tools.signal import remove_response
        >>> xml = Path("example_response.xml").read_bytes()
        >>> original = SAC.from_file("example.sac").seismogram
        >>> response = StationXML.from_bytes(xml, time=original.begin_time).response
        >>> seismogram = remove_response(original, response, clone=True)
        >>> len(seismogram.data) == len(original.data)
        True
        >>>
        ```

        Full spectral deconvolution, detrended and tapered first to avoid the
        wraparound artefacts described above. $f_4$ is bounded by both the
        seismogram's own Nyquist and the digital stages' (a stage is only meaningful
        up to half its own `input_sample_rate`); $f_1$ is read off the analog poles'
        own corner, below which deconvolution mostly amplifies sensor noise. Neither
        bound is computed automatically — the right choice is study-dependent (e.g.
        teleseismic earthquakes vs. ambient noise), so this is left to the caller:

        ```python
        >>> from pysmo.functions import detrend, taper
        >>> nyquist = 0.5 / original.delta.total_seconds()
        >>> stage_nyquist = min(stage.input_sample_rate / 2 for stage in response.stages)
        >>> f4 = 0.8 * min(nyquist, stage_nyquist)
        >>> f3 = f4 * 0.9
        >>> f1 = min(abs(pole) for pole in response.poles if pole != 0) / 10
        >>> f2 = f1 * 10
        >>> pre_filt = (f1, f2, f3, f4)
        >>> prepped = detrend(original, clone=True)
        >>> taper(prepped, 0.05)
        >>> deconvolved = remove_response(prepped, response, pre_filt=pre_filt, clone=True)
        >>> len(deconvolved.data) == len(original.data)
        True
        >>>
        ```

        !!! tip "Check the data, not just the instrument"

            $f_1$–$f_4$ above are chosen from the instrument and the
            sampling rate — but deconvolution divides by the response
            across that whole band, so what actually determines whether the
            result is trustworthy is the *data's* own amplitude at each of
            those frequencies, not just where the instrument and sample
            rate look reasonable on paper. A technically-defensible
            `pre_filt` can still amplify noise into a poor result if the
            data itself has little real amplitude somewhere within that
            band.

        With the earthquake's own dominant period band sitting well within
        `response`'s flat passband, the sensitivity-only and full-deconvolution paths
        agree closely in both amplitude and shape:

        ```python
        >>> import numpy as np
        >>> gain_only = remove_response(prepped, response, clone=True)
        >>> gain_only_rms = np.sqrt(np.mean(gain_only.data**2))
        >>> deconvolved_rms = np.sqrt(np.mean(deconvolved.data**2))
        >>> round(float(gain_only_rms / deconvolved_rms), 3)  # ~1: amplitude match
        1.082
        >>> round(float(np.corrcoef(gain_only.data, deconvolved.data)[0, 1]), 3)  # ~1: shape match
        0.926
        >>>
        ```

        Seeing the two paths plotted together makes that agreement concrete
        rather than abstract:

        ```python
        >>> from pysmo.tools.plotutils import plotseis
        >>> fig = plotseis(gain_only, deconvolved)
        >>> _ = fig.gca().set_ylabel(f"Velocity ({response.input_units})")
        >>> _ = fig.gca().legend(["Sensitivity only", "Full deconvolution"])
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig = plotseis(gain_only, deconvolved)
        ...     _ = fig.gca().set_ylabel(f"Velocity ({response.input_units})")
        ...     _ = fig.gca().legend(["Sensitivity only", "Full deconvolution"])
        ...     fig.savefig(
        ...         savedir / "response_removal_comparison-dark.png",
        ...         transparent=True,
        ...         bbox_inches="tight",
        ...     )
        ...
        ...     plt.style.use("default")
        ...     fig = plotseis(gain_only, deconvolved)
        ...     _ = fig.gca().set_ylabel(f"Velocity ({response.input_units})")
        ...     _ = fig.gca().legend(["Sensitivity only", "Full deconvolution"])
        ...     fig.savefig(
        ...         savedir / "response_removal_comparison.png",
        ...         transparent=True,
        ...         bbox_inches="tight",
        ...     )
        >>>
        ```
        -->

        <figure markdown="span">
        ![Sensitivity-only vs full deconvolution](../../../images/sybil/response_removal_comparison.png#only-light){ loading=lazy }
        ![Sensitivity-only vs full deconvolution](../../../images/sybil/response_removal_comparison-dark.png#only-dark){ loading=lazy }
        </figure>
    """
    if len(seismogram.data) == 0:
        raise ValueError("Cannot remove response from an empty seismogram.")

    if pre_filt is None:
        if response.reference_sensitivity is None:
            raise ValueError(
                "remove_response's sensitivity-only path (pre_filt=None) "
                "requires response.reference_sensitivity, which is None on "
                "this response. overall_sensitivity is not a substitute: it "
                "has response's A0 normalisation factor folded in and would "
                "mis-scale the result. Either supply reference_sensitivity "
                "(SAC PZ's SENSITIVITY header or StationXML's "
                "InstrumentSensitivity/Value) or pass pre_filt for full "
                "spectral deconvolution, which only needs overall_sensitivity."
            )
        if clone:
            seismogram = deepcopy(seismogram)
        seismogram.data = seismogram.data / response.reference_sensitivity
        return seismogram if clone else None

    dt = seismogram.delta.total_seconds()
    if dt <= 0:
        raise ValueError("Seismogram delta must be positive.")
    nyquist = 0.5 / dt

    f1, f2, f3, f4 = pre_filt
    if f1 <= 0:
        raise ValueError(
            f"pre_filt's lower corner ({f1}) must be above 0: a velocity- or "
            "acceleration-output sensor has a zero at DC by construction, so "
            "f1 <= 0 would divide by that zero."
        )
    if not (f1 < f2 <= f3 < f4):
        raise ValueError(
            f"pre_filt corners {pre_filt} must satisfy f1 < f2 <= f3 < f4."
        )
    if f4 > nyquist:
        raise ValueError(
            f"pre_filt's upper corner ({f4}) exceeds the seismogram's "
            f"Nyquist frequency ({nyquist})."
        )

    if clone:
        seismogram = deepcopy(seismogram)

    freqs = np.fft.rfftfreq(len(seismogram.data), d=dt)

    h = _analog_transfer_function(response, freqs)

    if isinstance(response, StagedResponse):
        h = h * _digital_transfer_function(response, freqs)
        has_stages = bool(response.stages)
        if has_stages:
            stage_nyquist = (
                min(stage.input_sample_rate for stage in response.stages) / 2
            )
            if f4 > 0.8 * stage_nyquist:
                warnings.warn(
                    "pre_filt's upper corner is above 80% of the digital "
                    "stages' own Nyquist frequency (half the slowest "
                    "stage's input_sample_rate): scipy.signal.freqz is "
                    "periodic, so evaluating a decimation stage beyond its "
                    "own Nyquist returns an aliased, non-physical value "
                    "rather than the stage's actual roll-off. Bound f4 by "
                    "min(seismogram_nyquist, stage_nyquist) instead.",
                    UserWarning,
                    stacklevel=2,
                )
    else:
        has_stages = False

    if not has_stages and f4 > 0.8 * nyquist:
        warnings.warn(
            "pre_filt's upper corner is above 80% of the Nyquist "
            "frequency, but response has no digital stages (e.g. a SAC "
            "PZ-derived response): the analog-only approximation does "
            "not account for the roll-off/phase a real digitiser's "
            "decimation filter contributes near its own Nyquist.",
            UserWarning,
            stacklevel=2,
        )

    taper = _pre_filt_taper(freqs, pre_filt)
    # Frequencies outside (f1, f4) are already excluded by the taper (0
    # there); dividing by h at those points is pointless and, if h is
    # also 0 (e.g. DC for a sensor with a zero at the origin), would turn
    # a harmless 0 into 0/0 = nan. Skip the division wherever taper == 0.
    filt = np.divide(
        taper, h, out=np.zeros_like(taper, dtype=complex), where=taper != 0
    )

    spectrum = np.fft.rfft(seismogram.data)
    seismogram.data = np.fft.irfft(spectrum * filt, n=len(seismogram.data))

    return seismogram if clone else None
