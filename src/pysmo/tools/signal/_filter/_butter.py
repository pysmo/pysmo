from copy import deepcopy
from typing import Literal, overload

from scipy.signal import iirfilter, sosfilt, sosfiltfilt

from pysmo import Seismogram
from pysmo.typing import PositiveInt

from ._registry import register_filter


@overload
def bandpass(
    seismogram: Seismogram,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def bandpass[T: Seismogram](
    seismogram: T,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[True],
) -> T: ...


@register_filter
def bandpass[T: Seismogram](
    seismogram: T,
    freqmin: float = 0.1,
    freqmax: float = 0.5,
    corners: PositiveInt = 2,
    zerophase: bool = False,
    *,
    clone: bool = False,
) -> T | None:
    """Apply a bandpass filter to the input seismogram.

    Args:
        seismogram: The input seismogram to be filtered.
        freqmin: The minimum frequency of the bandpass filter (in Hz).
        freqmax: The maximum frequency of the bandpass filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If `True`, apply the filter in both forward and reverse
            directions to achieve zero phase distortion.
        clone: If `True`, return a new Seismogram object with the filtered
            data. If `False`, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    low = freqmin / fe
    high = freqmax / fe

    if not (0 < low < 1):
        raise ValueError(
            f"freqmin ({freqmin}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if not (0 < high < 1):
        raise ValueError(
            f"freqmax ({freqmax}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if freqmin >= freqmax:
        raise ValueError("freqmin must be less than freqmax.")

    sos = iirfilter(corners, [low, high], btype="band", ftype="butter", output="sos")

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None


def _zerophase_causal_ratio(corners: PositiveInt) -> float:
    r"""Ratio between a zero-phase and single-pass Butterworth filter's actual -3dB point.

    A single-pass Butterworth filter's -3dB point sits exactly at its nominal
    design corner. Applying the same filter forward and backward (as
    [`bandpass`][pysmo.tools.signal.bandpass] does with `zerophase=True`, via
    [`sosfiltfilt`][scipy.signal.sosfiltfilt]) squares its magnitude
    response, which pulls the actual -3dB point inward from the nominal
    corner by this ratio:

    $$
    \text{ratio} = (\sqrt{2} - 1)^{1 / (2\,\text{corners})}
    $$

    `ratio` is always in $(0, 1)$: it approaches 0 as `corners` approaches 0,
    and approaches 1 as `corners` grows without bound (a steeper filter's
    actual -3dB point sits closer to its nominal corner). Shared by
    [`causal_band`][pysmo.tools.signal.causal_band] and
    [`zerophase_band`][pysmo.tools.signal.zerophase_band], the two public
    frequency corrections built from it.

    Args:
        corners: The number of corners (poles) of the single-pass filter
            (not the doubled order used internally for a zero-phase
            filter's forward-backward pass).

    Returns:
        The ratio, strictly between 0 and 1.
    """
    return (2**0.5 - 1) ** (1 / (2 * corners))


def causal_band(
    freqmin: float, freqmax: float, corners: PositiveInt
) -> tuple[float, float]:
    r"""Corner frequencies for a causal filter whose actual -3dB point matches a zero-phase filter's.

    Use this when adding a causal (single-pass) alternative to an existing
    zero-phase-filtered workflow. Passing the same nominal `freqmin`/
    `freqmax` to [`bandpass`][pysmo.tools.signal.bandpass] with
    `zerophase=False` gives the causal filter a wider effective passband
    than the zero-phase one: a single-pass Butterworth's -3dB point sits
    exactly at its nominal corner, while a zero-phase filter's is pulled
    inward, so the causal filter passes more energy near the band edges.
    `causal_band` computes the narrower design corners that correct for
    this.

    `corners` is the zero-phase filter's own order, not the doubled order
    [`bandpass`][pysmo.tools.signal.bandpass] needs for `zerophase=False` to
    match a zero-phase filter's rolloff steepness.

    The match is close, not exact: a Butterworth bandpass filter's two edges
    interact, so the residual grows for narrower bands or lower `corners`,
    and grows further at low sample rates relative to `freqmax` (concrete
    numbers in the example below).

    Both corrected edges move inward, so `corners` also affects whether a
    band stays valid, not just `freqmin < freqmax`: a narrow enough band
    combined with a low enough `corners` can push `freqmin_causal` above
    `freqmax_causal`, which raises `ValueError`.

    Args:
        freqmin: Nominal minimum frequency (in Hz) of the zero-phase filter.
        freqmax: Nominal maximum frequency (in Hz) of the zero-phase filter.
        corners: The zero-phase filter's number of corners (poles).

    Returns:
        The `(freqmin, freqmax)` design frequencies (in Hz) for the causal
        filter, with `freqmin` moved up and `freqmax` moved down from the
        input values.

    Raises:
        ValueError: If the correction would push `freqmin_causal` above
            `freqmax_causal` (too narrow a band for `corners`).

    Examples:
        Overlaying the three filter variants
        [`bandpass`][pysmo.tools.signal.bandpass] can produce for a given
        `freqmin`/`freqmax`/`corners`: zero-phase, uncorrected causal, and
        `causal_band`-corrected causal. Both causal designs below use
        `2 * corners` poles, matching the rolloff steepness of the
        zero-phase filter (`sosfiltfilt` applies it forward and backward,
        doubling the effective order). Parameters use a realistic broadband
        passband and sample rate, chosen without tuning to minimise the
        visible gap:

        ```python
        >>> import numpy as np
        >>> from scipy.signal import iirfilter, sosfreqz
        >>> from pysmo.tools.signal import causal_band
        >>> freqmin, freqmax, corners = 0.05, 2.0, 2
        >>> fs = 20.0
        >>> nyquist = fs / 2
        >>> freqmin_causal, freqmax_causal = causal_band(freqmin, freqmax, corners)
        >>> round(freqmin_causal, 4), round(freqmax_causal, 4)
        (0.0623, 1.6045)
        >>> sos_zerophase = iirfilter(
        ...     corners, [freqmin / nyquist, freqmax / nyquist],
        ...     btype="band", ftype="butter", output="sos",
        ... )
        >>> sos_causal_uncorrected = iirfilter(
        ...     2 * corners, [freqmin / nyquist, freqmax / nyquist],
        ...     btype="band", ftype="butter", output="sos",
        ... )
        >>> sos_causal_corrected = iirfilter(
        ...     2 * corners, [freqmin_causal / nyquist, freqmax_causal / nyquist],
        ...     btype="band", ftype="butter", output="sos",
        ... )
        >>>
        ```

        The zero-phase magnitude is the single-pass response squared
        (`sosfiltfilt` applies the filter twice); the causal variants are
        the direct single-pass response:

        ```python
        >>> target_db = -20 * np.log10(2**0.5)  # -3.01 dB
        >>> def crossing(sos, zerophase, edge_freq, margin=0.6):
        ...     w, h = sosfreqz(sos, worN=8000, fs=fs)
        ...     mag = np.abs(h) ** 2 if zerophase else np.abs(h)
        ...     db = 20 * np.log10(mag + 1e-300)
        ...     mask = (w > edge_freq * (1 - margin)) & (w < edge_freq * (1 + margin))
        ...     seg_w, seg_d = w[mask], db[mask] - target_db
        ...     j = np.where(np.diff(np.sign(seg_d)) != 0)[0]
        ...     best = j[np.argmin(np.abs(seg_w[j] - edge_freq))]
        ...     frac = -seg_d[best] / (seg_d[best + 1] - seg_d[best])
        ...     return seg_w[best] + frac * (seg_w[best + 1] - seg_w[best])
        >>> zerophase_edge = crossing(sos_zerophase, True, freqmax)
        >>> causal_corrected_edge = crossing(sos_causal_corrected, False, freqmax)
        >>> residual_pct = abs(causal_corrected_edge - zerophase_edge) / zerophase_edge * 100
        >>> round(float(residual_pct), 1)
        2.4
        >>>
        ```

        The corrected marker lands close to the zero-phase one, unlike the
        uncorrected marker, which stays at the nominal `freqmax=2.0` corner.
        A residual of a few percent remains between the corrected and
        zero-phase markers (edge interaction, plus some Nyquist-proximity
        effect at this sample rate).

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> def _plot():
        ...     fig, ax = plt.subplots(figsize=(8, 5))
        ...     ax.axhline(target_db, color="grey", linestyle="--", linewidth=1, label="-3 dB")
        ...     curves = {
        ...         "Zero-phase (sosfiltfilt)": (sos_zerophase, True),
        ...         "Causal, uncorrected": (sos_causal_uncorrected, False),
        ...         "Causal, corrected (causal_band)": (sos_causal_corrected, False),
        ...     }
        ...     edges = {}
        ...     for label, (sos, zerophase) in curves.items():
        ...         w, h = sosfreqz(sos, worN=8000, fs=fs)
        ...         mag = np.abs(h) ** 2 if zerophase else np.abs(h)
        ...         db = 20 * np.log10(mag + 1e-300)
        ...         line, = ax.semilogx(w, db, label=label)
        ...         edges[label] = [crossing(sos, zerophase, e) for e in (freqmin, freqmax)]
        ...         for cf in edges[label]:
        ...             ax.plot(cf, target_db, marker="o", color=line.get_color(), markersize=6)
        ...     pct = (
        ...         abs(edges["Causal, corrected (causal_band)"][1] - edges["Zero-phase (sosfiltfilt)"][1])
        ...         / edges["Zero-phase (sosfiltfilt)"][1] * 100
        ...     )
        ...     ax.annotate(
        ...         f"residual ≈ {pct:.1f}%",
        ...         xy=(edges["Causal, corrected (causal_band)"][1], target_db),
        ...         xytext=(10, -25), textcoords="offset points", fontsize=8,
        ...         arrowprops=dict(arrowstyle="->", color="grey"),
        ...     )
        ...     ax.set_xlim(0.01, nyquist)
        ...     ax.set_ylim(-40, 5)
        ...     ax.set_xlabel("Frequency [Hz]")
        ...     ax.set_ylabel("Magnitude [dB]")
        ...     ax.legend(loc="lower left", fontsize=8)
        ...     fig.tight_layout()
        ...     return fig
        ...
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig = _plot()
        ...     fig.savefig(
        ...         savedir / "causal_band_response-dark.png",
        ...         transparent=True,
        ...         bbox_inches="tight",
        ...     )
        ...
        ...     plt.style.use("default")
        ...     fig = _plot()
        ...     fig.savefig(
        ...         savedir / "causal_band_response.png",
        ...         transparent=True,
        ...         bbox_inches="tight",
        ...     )
        >>>
        ```
        -->

        <figure markdown="span">
        ![Zero-phase vs causal Butterworth magnitude response](../../../images/sybil/causal_band_response.png#only-light){ loading=lazy }
        ![Zero-phase vs causal Butterworth magnitude response](../../../images/sybil/causal_band_response-dark.png#only-dark){ loading=lazy }
        </figure>
    """
    ratio = _zerophase_causal_ratio(corners)
    freqmin_causal, freqmax_causal = freqmin / ratio, freqmax * ratio
    if freqmin_causal >= freqmax_causal:
        raise ValueError(
            f"causal_band({freqmin}, {freqmax}, {corners}) would invert the "
            + f"band: freqmin_causal ({freqmin_causal}) >= freqmax_causal "
            + f"({freqmax_causal})."
        )
    return freqmin_causal, freqmax_causal


def zerophase_band(
    freqmin: float, freqmax: float, corners: PositiveInt
) -> tuple[float, float]:
    r"""Corner frequencies for a zero-phase filter whose actual -3dB point matches a causal filter's.

    The exact inverse of [`causal_band`][pysmo.tools.signal.causal_band]:
    use this when you have causal (single-pass) design frequencies already
    chosen — from an existing causal filtering workflow, or from
    `causal_band` itself — and want the zero-phase nominal frequencies whose
    actual passband matches them, independent of any particular application.

    Converts **causal design** corner frequencies to the wider nominal
    frequencies a **zero-phase** filter needs so that its actual (inward-shifted)
    -3dB point lands close to the causal filter's actual (nominal) -3dB point.

    The inverse is exact and closed-form — the same ratio `causal_band`
    uses, with multiplication and division swapped — not an approximation
    or an iterative solve. Both corrected edges move outward from the input band,
    the opposite direction from `causal_band`. The same close-but-not-exact
    caveat documented on `causal_band` applies here too: matching -3dB
    points between a digital causal and zero-phase Butterworth bandpass
    filter is close, not exact.

    Args:
        freqmin: Causal design minimum frequency (in Hz).
        freqmax: Causal design maximum frequency (in Hz).
        corners: The zero-phase filter's number of corners (poles) — the
            same `corners` value used to derive the causal filter's design
            frequencies, not the doubled order the causal filter itself uses.

    Returns:
        The `(freqmin, freqmax)` nominal frequencies (in Hz) for the
        zero-phase filter, with `freqmin` moved down and `freqmax` moved up
        from the input values.

    Examples:
        Round-trip with `causal_band` recovers the original band exactly:

        ```pycon
        >>> from pysmo.tools.signal import causal_band, zerophase_band
        >>> band = (0.05, 2.0)
        >>> corners = 2
        >>> causal = causal_band(*band, corners)
        >>> recovered = zerophase_band(*causal, corners)
        >>> [round(f, 10) for f in recovered]
        [0.05, 2.0]

        ```
    """
    ratio = _zerophase_causal_ratio(corners)
    return freqmin * ratio, freqmax / ratio


@overload
def highpass(
    seismogram: Seismogram,
    freqmin: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def highpass[T: Seismogram](
    seismogram: T,
    freqmin: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[True],
) -> T: ...


@register_filter
def highpass[T: Seismogram](
    seismogram: T,
    freqmin: float = 0.1,
    corners: PositiveInt = 2,
    zerophase: bool = False,
    *,
    clone: bool = False,
) -> T | None:
    """Apply a highpass filter to the input seismogram.

    Args:
        seismogram: The input seismogram to be filtered.
        freqmin: The minimum frequency of the highpass filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If `True`, apply the filter in both forward and reverse
            directions to achieve zero phase distortion.
        clone: If `True`, return a new Seismogram object with the filtered
            data. If `False`, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    low = freqmin / fe

    if not (0 < low < 1):
        raise ValueError(
            f"freqmin ({freqmin}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )

    sos = iirfilter(corners, low, btype="high", ftype="butter", output="sos")

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None


@overload
def lowpass(
    seismogram: Seismogram,
    freqmax: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def lowpass[T: Seismogram](
    seismogram: T,
    freqmax: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[True] = ...,
) -> T: ...


@register_filter
def lowpass[T: Seismogram](
    seismogram: T,
    freqmax: float = 0.5,
    corners: PositiveInt = 2,
    zerophase: bool = False,
    *,
    clone: bool = False,
) -> T | None:
    """Apply a lowpass filter to the input seismogram.

    Args:
        seismogram: The input seismogram to be filtered.
        freqmax: The maximum frequency of the lowpass filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If `True`, apply the filter in both forward and reverse
            directions to achieve zero phase distortion.
        clone: If `True`, return a new Seismogram object with the filtered
            data. If `False`, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    high = freqmax / fe

    if not (0 < high < 1):
        raise ValueError(
            f"freqmax ({freqmax}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )

    sos = iirfilter(corners, high, btype="low", ftype="butter", output="sos")

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None


@overload
def bandstop(
    seismogram: Seismogram,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def bandstop[T: Seismogram](
    seismogram: T,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: PositiveInt = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[True],
) -> T: ...


@register_filter
def bandstop[T: Seismogram](
    seismogram: T,
    freqmin: float = 0.1,
    freqmax: float = 0.5,
    corners: PositiveInt = 2,
    zerophase: bool = False,
    *,
    clone: bool = False,
) -> T | None:
    """Apply a bandstop filter to the input seismogram.

    Args:
        seismogram: The input seismogram to be filtered.
        freqmin: The minimum frequency of the bandstop filter (in Hz).
        freqmax: The maximum frequency of the bandstop filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If `True`, apply the filter in both forward and reverse
            directions to achieve zero phase distortion.
        clone: If `True`, return a new Seismogram object with the filtered
            data. If `False`, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    low = freqmin / fe
    high = freqmax / fe

    if not (0 < low < 1):
        raise ValueError(
            f"freqmin ({freqmin}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if not (0 < high < 1):
        raise ValueError(
            f"freqmax ({freqmax}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if freqmin >= freqmax:
        raise ValueError("freqmin must be less than freqmax.")

    sos = iirfilter(
        corners, [low, high], btype="bandstop", ftype="butter", output="sos"
    )

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None
