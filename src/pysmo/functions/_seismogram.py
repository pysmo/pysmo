from pysmo import Seismogram
from pysmo.typing import (
    PositiveTimedelta,
    NonNegativeTimedelta,
    NonNegativeNumber,
    UnitFloat,
)
from copy import deepcopy
from datetime import datetime, timedelta
from math import floor
from typing import Any, Literal, overload, TYPE_CHECKING
from beartype import beartype
import scipy.signal
import numpy as np

if TYPE_CHECKING:
    from numpy.lib._arraypad_impl import _ModeKind, _ModeFunc

__all__ = [
    "crop",
    "detrend",
    "normalize",
    "pad",
    "resample",
    "taper",
    "time2index",
    "window",
]

# Scipy windows can be a string, a float (beta), or a tuple (name, param)
type _WindowType = str | float | tuple[str, float] | tuple[str, float, float]


@overload
def crop(
    seismogram: Seismogram,
    begin_time: datetime,
    end_time: datetime,
    clone: Literal[False] = ...,
) -> None: ...
@overload
def crop[T: Seismogram](
    seismogram: T, begin_time: datetime, end_time: datetime, clone: Literal[True]
) -> T: ...


def crop[T: Seismogram](
    seismogram: T, begin_time: datetime, end_time: datetime, clone: bool = False
) -> None | T:
    """Shorten a seismogram by providing new begin and end times.

    This function calculates the indices corresponding to the provided new
    begin and end times using [`time2index`][pysmo.functions.time2index], then
    slices the seismogram `data` array accordingly and updates the
    `begin_time`.

    Args:
        seismogram: [`Seismogram`][pysmo.Seismogram] object.
        begin_time: New begin time.
        end_time: New end time.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Cropped [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Raises:
        ValueError: If new begin time is after new end time.

    Examples:
        ```python
        >>> from pysmo.functions import crop
        >>> from pysmo.classes import SAC
        >>> from datetime import timedelta
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> new_begin_time = sac_seis.begin_time + timedelta(seconds=10)
        >>> new_end_time = sac_seis.end_time - timedelta(seconds=10)
        >>> crop(sac_seis, new_begin_time, new_end_time)
        >>>
        ```
    """

    if begin_time > end_time:
        raise ValueError("New begin_time cannot be after new end_time")

    start_index = time2index(seismogram, begin_time)
    end_index = time2index(seismogram, end_time)

    if clone is True:
        seismogram = deepcopy(seismogram)

    seismogram.data = seismogram.data[start_index : end_index + 1]
    seismogram.begin_time += seismogram.delta * start_index

    if clone is True:
        return seismogram
    return None


# --8<-- [start:detrend]
@overload
def detrend(seismogram: Seismogram, clone: Literal[False] = ...) -> None: ...


@overload
def detrend[T: Seismogram](seismogram: T, clone: Literal[True]) -> T: ...


def detrend[T: Seismogram](seismogram: T, clone: bool = False) -> None | T:
    """Remove linear and/or constant trends from a seismogram.

    Args:
        seismogram: Seismogram object.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Detrended [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        ```python
        >>> import numpy as np
        >>> import pytest
        >>> from pysmo.functions import detrend
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> 0 == pytest.approx(np.mean(sac_seis.data), abs=1e-11)
        np.False_
        >>> detrend(sac_seis)
        >>> 0 == pytest.approx(np.mean(sac_seis.data), abs=1e-11)
        np.True_
        >>>
        ```
    """
    if clone is True:
        seismogram = deepcopy(seismogram)

    seismogram.data = scipy.signal.detrend(seismogram.data)

    if clone is True:
        return seismogram
    return None


# --8<-- [end:detrend]


@overload
def normalize(
    seismogram: Seismogram,
    t1: datetime | None = ...,
    t2: datetime | None = ...,
    clone: Literal[False] = ...,
) -> None: ...
@overload
def normalize[T: Seismogram](
    seismogram: T,
    t1: datetime | None = ...,
    t2: datetime | None = ...,
    *,
    clone: Literal[True],
) -> T: ...


def normalize[T: Seismogram](
    seismogram: T,
    t1: datetime | None = None,
    t2: datetime | None = None,
    clone: bool = False,
) -> None | T:
    """Normalize a seismogram with its absolute max value.

    Args:
        seismogram: Seismogram object.
        t1: Optionally restrict searching of maximum to time after this time.
        t2: Optionally restrict searching of maximum to time before this time.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Normalized [`Seismogram`][pysmo.Seismogram] object if `clone=True`.

    Examples:
        ```python
        >>> import numpy as np
        >>> from pysmo.functions import normalize
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> normalize(sac_seis)
        >>> -1 <= np.max(sac_seis.data) <= 1
        np.True_
        >>>
        ```
    """

    if clone is True:
        seismogram = deepcopy(seismogram)

    start_index, end_index = None, None

    if t1 is not None:
        start_index = time2index(seismogram, t1)

    if t2 is not None:
        end_index = time2index(seismogram, t2)

    seismogram.data /= np.max(np.abs(seismogram.data[start_index:end_index]))

    if clone is True:
        return seismogram

    return None


@overload
def pad[T: Seismogram](
    seismogram: T,
    begin_time: datetime,
    end_time: datetime,
    mode: "_ModeKind | _ModeFunc" = "constant",
    *,
    clone: Literal[True],
    **kwargs: Any,
) -> T: ...


@overload
def pad(
    seismogram: Seismogram,
    begin_time: datetime,
    end_time: datetime,
    mode: "_ModeKind | _ModeFunc" = "constant",
    clone: Literal[False] = False,
    **kwargs: Any,
) -> None: ...


def pad[T: Seismogram](
    seismogram: T,
    begin_time: datetime,
    end_time: datetime,
    mode: "_ModeKind | _ModeFunc" = "constant",
    clone: bool = False,
    **kwargs: Any,
) -> None | T:
    """Pad seismogram data.

    This function calculates the indices corresponding to the provided new
    begin and end times using [`time2index`][pysmo.functions.time2index], then
    pads the [`data`][pysmo.Seismogram.data] array using
    [`numpy.pad`][numpy.pad] and updates the
    [`begin_time`][pysmo.Seismogram.begin_time]. Note that the actual begin and
    end times are set by indexing, so they may be slightly different than the
    provided input begin and end times.

    Args:
        seismogram: [`Seismogram`][pysmo.Seismogram] object.
        begin_time: New begin time.
        end_time: New end time.
        mode: Pad mode to use (see [`numpy.pad`][numpy.pad] for all modes).
        clone: Operate on a clone of the input seismogram.
        kwargs: Keyword arguments to pass to [`numpy.pad`][numpy.pad].

    Returns:
        Padded [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Raises:
        ValueError: If new begin time is after new end time.

    Examples:
        ```python
        >>> from pysmo.functions import pad
        >>> from pysmo.classes import SAC
        >>> from datetime import timedelta
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> original_length = len(sac_seis)
        >>> sac_seis.data
        array([2302., 2313., 2345., ..., 2836., 2772., 2723.], shape=(180000,))
        >>> new_begin_time = sac_seis.begin_time - timedelta(seconds=10)
        >>> new_end_time = sac_seis.end_time + timedelta(seconds=10)
        >>> pad(sac_seis, new_begin_time, new_end_time)
        >>> len(sac_seis) == original_length + 20 * (1 / sac_seis.delta.total_seconds())
        True
        >>> sac_seis.data
        array([0., 0., 0., ..., 0., 0., 0.], shape=(181000,))
        >>>
        ```
    """

    if begin_time > end_time:
        raise ValueError("New begin_time cannot be after new end_time")

    start_index = time2index(
        seismogram, begin_time, method="floor", allow_out_of_bounds=True
    )
    end_index = time2index(
        seismogram, end_time, method="ceil", allow_out_of_bounds=True
    )

    if clone is True:
        seismogram = deepcopy(seismogram)

    pad_before = max(0, -start_index)
    pad_after = max(0, end_index - (len(seismogram) - 1))

    if pad_before > 0 or pad_after > 0:
        seismogram.data = np.pad(
            seismogram.data,
            pad_width=(pad_before, pad_after),
            mode=mode,
            **kwargs,
        )
        seismogram.begin_time += seismogram.delta * min(0, start_index)

    if clone is True:
        return seismogram
    return None


@overload
def resample(
    seismogram: Seismogram, delta: PositiveTimedelta, clone: Literal[False] = ...
) -> None: ...


@overload
def resample[T: Seismogram](
    seismogram: T, delta: PositiveTimedelta, clone: Literal[True]
) -> T: ...


@beartype
def resample[T: Seismogram](
    seismogram: T, delta: PositiveTimedelta, clone: bool = False
) -> None | T:
    """Resample Seismogram data using the Fourier method.

    This function uses [`scipy.resample`][scipy.signal.resample] to resample
    the data to a new sampling interval. If the new sampling interval is
    identical to the current one, no action is taken.

    Args:
        seismogram: Seismogram object.
        delta: New sampling interval.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Resampled [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        ```python
        >>> from pysmo.functions import resample
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> len(sac_seis)
        180000
        >>> original_delta = sac_seis.delta
        >>> new_delta = original_delta * 2
        >>> resample(sac_seis, new_delta)
        >>> len(sac_seis)
        90000
        >>>
        ```
    """
    if clone is True:
        seismogram = deepcopy(seismogram)

    if delta != seismogram.delta:
        npts = int(len(seismogram) * seismogram.delta / delta)
        seismogram.data = scipy.signal.resample(seismogram.data, npts)
        seismogram.delta = delta

    if clone is True:
        return seismogram
    return None


@overload
def taper(
    seismogram: Seismogram,
    taper_width: NonNegativeTimedelta | UnitFloat,
    window_type: _WindowType = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def taper[T: Seismogram](
    seismogram: T,
    taper_width: NonNegativeTimedelta | UnitFloat,
    window_type: _WindowType = ...,
    *,
    clone: Literal[True],
) -> T: ...


@beartype
def taper[T: Seismogram](
    seismogram: T,
    taper_width: NonNegativeTimedelta | UnitFloat,
    window_type: _WindowType = "hann",
    clone: bool = False,
) -> None | T:
    """Apply a symmetric taper to the ends of a Seismogram.

    The [`taper()`][pysmo.functions.taper] function applies a symmetric taper to
    the data of a [`Seismogram`][pysmo.Seismogram] object. The taper width is
    understood as the portion of the seismogram affected by the taper window
    function. It can be provided as an absolute duration (non-negative
    [`timedelta`][datetime.timedelta]), or as a fraction of seismogram length
    ([`float`][float] between `0` and `1`). Internally, absolute durations are
    converted to fractions by dividing by the total seismogram duration, and
    absolute durations should therefore not exceed the total seismogram
    duration.

    The shape of the windowing function is calculated by calling the scipy
    [`get_window()`][scipy.signal.windows.get_window] function using the number
    of samples corresponding to the fraction specified above, then it is split
    in half and applied to the beginning and end of the seismogram data. Thus
    `taper_width=0` corresponds to a rectangular window (i.e. no tapering), and
    `taper_width=1` to a symmetric taper applied to the entire length of the
    seismogram. A value of e.g. `0.5` applies the "ramp up" portion of the
    window to the first quarter of the seismogram, while the "ramp down" portion
    of the window is applied to the last quarter.

    Warning:
        The scipy [`get_window()`][scipy.signal.windows.get_window] function
        is a helper function that calculates a large variety of window shapes,
        which do not all make sense in this application (e.g. boxcar or tukey).
        Users are encouraged to read the documentation of the actual window
        functions available via
        [`get_window()`][scipy.signal.windows.get_window] to see if they can be
        split in the middle and used as "ramp up" and "ramp down" functions.

    Args:
        seismogram: Seismogram object.
        taper_width: Width of the taper to use.
        window_type: Function to calculate taper shape (see
            [`get_window`][scipy.signal.windows.get_window] for valid inputs).
        clone: Operate on a clone of the input seismogram.

    Returns:
        Tapered [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        ```python
        >>> from pysmo.functions import taper, detrend
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> detrend(sac_seis)
        >>> sac_seis.data
        array([ 95.59652208, 106.59521819, 138.59391429, ..., 394.90004126,
               330.89873737, 281.89743348], shape=(180000,))
        >>> taper(sac_seis, 0.2)
        >>> sac_seis.data
        array([0.00000000e+00, 8.11814104e-07, 4.22204657e-06, ...,
               1.20300114e-05, 2.52007798e-06, 0.00000000e+00], shape=(180000,))
        >>>
        ```
    """

    nsamples: int
    if isinstance(taper_width, timedelta):
        nsamples = taper_width // seismogram.delta
    else:
        nsamples = floor(len(seismogram) * taper_width)

    if nsamples > len(seismogram):
        raise ValueError(
            "'taper_width' is too large. Total taper width may exceed the duration of the seismogram."
        )

    if clone is True:
        seismogram = deepcopy(seismogram)

    # Need at least 2 samples to apply a taper
    if nsamples >= 2:
        window = scipy.signal.windows.get_window(window_type, nsamples, fftbins=False)
        ramp_samples = nsamples // 2
        seismogram.data[:ramp_samples] *= window[:ramp_samples]
        seismogram.data[-ramp_samples:] *= window[-ramp_samples:]

    if clone is True:
        return seismogram
    return None


def time2index(
    seismogram: Seismogram,
    time: datetime,
    method: Literal["ceil", "floor", "round"] = "round",
    allow_out_of_bounds: bool = False,
) -> int:
    """Retuns data index corresponding to a given time.

    This function converts time to index of a seismogram's data array. In most
    cases the time will not have an exact match in the data array. This
    function allows choosing how to select the index to return when that is
    the case with the method parameter:

    - round: round to nearest index.
    - ceil: always round up to next higher index.
    - floor: always round down to next lower index.

    Args:
        seismogram: Seismogram object.
        time: Time to convert to index.
        method: Method to use for selecting the index to return.
        allow_out_of_bounds: If True, allow returning an index that is outside
            has no corresponding data point in the seismogram.

    Returns:
        Index of the sample corresponding to the given time.

    Raises:
        ValueError: If the calculated index is out of bounds and
            `allow_out_of_bounds` is not set to True.
    """

    if method == "ceil":
        index = np.ceil((time - seismogram.begin_time) / seismogram.delta)

    elif method == "floor":
        index = np.floor((time - seismogram.begin_time) / seismogram.delta)

    elif method == "round":
        index = np.round((time - seismogram.begin_time) / seismogram.delta)

    else:
        raise ValueError(
            "Invalid method provided. Valid options are 'ceil', 'floor', and 'round'."
        )

    if 0 <= index < len(seismogram) or allow_out_of_bounds is True:
        return int(index)

    raise ValueError(f"Invalid time provided, calculated {index=} is out of bounds.")


@overload
def window(
    seismogram: Seismogram,
    window_begin_time: datetime,
    window_end_time: datetime,
    ramp_width: NonNegativeTimedelta | NonNegativeNumber,
    window_type: _WindowType = ...,
    same_shape: bool = False,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def window[T: Seismogram](
    seismogram: T,
    window_begin_time: datetime,
    window_end_time: datetime,
    ramp_width: NonNegativeTimedelta | NonNegativeNumber,
    window_type: _WindowType = ...,
    *,
    same_shape: bool = False,
    clone: Literal[True],
) -> T: ...


@beartype
def window[T: Seismogram](
    seismogram: T,
    window_begin_time: datetime,
    window_end_time: datetime,
    ramp_width: NonNegativeTimedelta | NonNegativeNumber,
    window_type: _WindowType = "hann",
    same_shape: bool = False,
    clone: bool = False,
) -> None | T:
    """Returns an optionally padded and tapered window of a seismogram.

    This function combines the [`crop`][pysmo.functions.crop],
    [`detrend`][pysmo.functions.detrend], [`taper`][pysmo.functions.taper], and
    optionally [`pad`][pysmo.functions.pad] functions to return a 'windowed'
    seismogram. Its purpose is to focus on a specific time window of interest,
    while also (optionally) preserving the original seismogram length and
    tapering the signal before and after the window.

    Tip:
        Note that the window defined by `window_begin_time` and
        `window_end_time` *excludes* the tapered sections, so the total length
        of the window will be the provided window length plus the tapered
        sections of the signal. This behaviour is a bit different from
        [`taper()`][pysmo.functions.taper], where the taper is applied to the
        entire signal. In a sense the tapering here is applied to the 'outside'
        of the region of interest rather than the 'inside'.

    Args:
        seismogram: Seismogram object.
        window_begin_time: Begin time of the window.
        window_end_time: End time of the window.
        ramp_width: Duration of the taper on *each side*.

            - If `float`: calculated as a fraction of the window length.
            - If `timedelta`: used as absolute duration.

            Note: Total duration = window length + (2 * `ramp_width`).
        window_type: Taper method to use (see [`taper`][pysmo.functions.taper]).
        same_shape: If True, pad the seismogram to its original length after
            windowing.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Windowed [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        In this example we focus on a window starting 500 seconds after the
        `begin_time` of the seismogram and lasting for 1000 seconds. Setting the
        `ramp_width` to 250 seconds means that the actual window will start 250
        seconds earlier and end 250 seconds later than the specified window
        begin and end times.

        ```python
        >>> from pysmo.functions import window, detrend
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.plotutils import plotseis
        >>> from datetime import timedelta
        >>>
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> ramp_width = timedelta(seconds=250)
        >>> window_begin_time = sac_seis.begin_time + timedelta(seconds=500)
        >>> window_end_time = window_begin_time + timedelta(seconds=1000)
        >>> windowed_seis = window(sac_seis, window_begin_time, window_end_time, ramp_width, same_shape=True, clone=True)
        >>> detrend(sac_seis)
        >>> fig = plotseis(sac_seis, windowed_seis)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig = plotseis(sac_seis, windowed_seis)
        ...     fig.savefig(savedir / "functions_window-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig = plotseis(sac_seis, windowed_seis)
        ...     fig.savefig(savedir / "functions_window.png", transparent=True)
        >>>
        ```
        -->

        <figure markdown="span">
        ![Functions window](../../images/functions/functions_window.png#only-light){ loading=lazy }
        ![Functions window](../../images/functions/functions_window-dark.png#only-dark){ loading=lazy }
        </figure>
    """

    begin_time, end_time = seismogram.begin_time, seismogram.end_time

    ramp_duration: timedelta
    if isinstance(ramp_width, (float, int)):
        ramp_duration = ramp_width * (window_end_time - window_begin_time)
    else:
        ramp_duration = ramp_width

    window_begin_time -= ramp_duration
    window_end_time += ramp_duration

    if clone is True:
        seismogram = crop(seismogram, window_begin_time, window_end_time, clone=True)
    else:
        crop(seismogram, window_begin_time, window_end_time)
    detrend(seismogram)
    taper(seismogram, taper_width=ramp_duration * 2, window_type=window_type)
    if same_shape is True:
        pad(seismogram, begin_time, end_time)

    if clone is True:
        return seismogram
    return None
