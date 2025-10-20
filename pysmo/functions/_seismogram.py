from pysmo import Seismogram
from copy import deepcopy
from datetime import datetime, timedelta
from math import floor
from typing import Any, Literal, overload
from functools import singledispatch
import scipy.signal
import numpy as np
from typing import TYPE_CHECKING

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

    Parameters:
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


@overload
def detrend(seismogram: Seismogram, clone: Literal[False] = ...) -> None: ...
@overload
def detrend[T: Seismogram](seismogram: T, clone: Literal[True]) -> T: ...


def detrend[T: Seismogram](seismogram: T, clone: bool = False) -> None | T:
    """Remove linear and/or constant trends from a seismogram.

    Parameters:
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

    Parameters:
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

    Parameters:
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
    seismogram: Seismogram, delta: timedelta, clone: Literal[False] = ...
) -> None: ...


@overload
def resample[T: Seismogram](
    seismogram: T, delta: timedelta, clone: Literal[True]
) -> T: ...


def resample[T: Seismogram](
    seismogram: T, delta: timedelta, clone: bool = False
) -> None | T:
    """Resample Seismogram data using the Fourier method.

    This function uses [`scipy.resample`][scipy.signal.resample] to resample
    the data to a new sampling interval. If the new sampling interval is
    identical to the current one, no action is taken.

    Parameters:
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
    taper_width: timedelta | float,
    taper_method: Literal["bartlett", "blackman", "hamming", "hanning", "kaiser"] = ...,
    beta: float = ...,
    left: bool = ...,
    right: bool = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def taper[T: Seismogram](
    seismogram: T,
    taper_width: timedelta | float,
    taper_method: Literal["bartlett", "blackman", "hamming", "hanning", "kaiser"] = ...,
    beta: float = ...,
    left: bool = ...,
    right: bool = ...,
    *,
    clone: Literal[True],
) -> T: ...


def taper[T: Seismogram](
    seismogram: T,
    taper_width: timedelta | float,
    taper_method: Literal[
        "bartlett", "blackman", "hamming", "hanning", "kaiser"
    ] = "hanning",
    beta: float = 14.0,
    left: bool = True,
    right: bool = True,
    clone: bool = False,
) -> None | T:
    """Apply a symetric taper to the ends of a Seismogram.

    The [`taper()`][pysmo.functions.taper] function applies a taper to the data
    at one or both ends of a [`Seismogram`][pysmo.Seismogram] object. The width
    of this taper can be provided as either positive
    [`timedelta`][datetime.timedelta] or as a fraction of the total seismogram
    length. In both cases the total width of the taper (i.e. left and right
    side combined) should not exceed the length of the seismogram.

    Different methods for calculating the shape of the taper may be specified.
    They are all derived from the corresponding `numpy` window functions:

    - [`numpy.bartlett`][numpy.bartlett]
    - [`numpy.blackman`][numpy.blackman]
    - [`numpy.hamming`][numpy.hamming]
    - [`numpy.hanning`][numpy.hanning]
    - [`numpy.kaiser`][numpy.kaiser]

    Parameters:
        seismogram: Seismogram object.
        taper_width: With of the taper to use.
        taper_method: Taper method to use.
        beta: beta value for the Kaiser window function (ignored for other methods).
        left: Apply taper to the left side of the seismogram.
        right: Apply taper to the right side of the seismogram.
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
        >>> taper(sac_seis, 0.1)
        >>> sac_seis.data
        array([0.00000000e+00, 8.11814104e-07, 4.22204657e-06, ...,
               1.20300114e-05, 2.52007798e-06, 0.00000000e+00], shape=(180000,))
        >>>
        ```
    """

    def calc_window_data(window_length: int) -> np.ndarray:
        if taper_method == "bartlett":
            return np.bartlett(window_length)
        elif taper_method == "blackman":
            return np.blackman(window_length)
        elif taper_method == "hamming":
            return np.hamming(window_length)
        elif taper_method == "hanning":
            return np.hanning(window_length)
        elif taper_method == "kaiser":
            return np.kaiser(window_length, beta)

    @singledispatch
    def calc_samples(taper_width: Any) -> int:
        raise TypeError(f"Unsupported type for 'taper_width': {type(taper_width)}")

    @calc_samples.register(float)
    def _(taper_width: float) -> int:
        """Calculate the number of samples to taper from an int."""
        return floor(len(seismogram) * taper_width)

    @calc_samples.register(timedelta)
    def _(taper_width: timedelta) -> int:
        """Calculate the number of samples to taper from a timedelta."""
        return floor(taper_width / seismogram.delta)

    if clone is True:
        seismogram = deepcopy(seismogram)

    if left is False and right is False:
        return seismogram if clone is True else None

    nsamples = calc_samples(taper_width)

    if nsamples * (left + right) > len(seismogram):
        raise ValueError(
            "'taper_width' is too large. Total taper width may exceed the length of the seismogram."
        )

    if nsamples > 0:
        taper_data = np.ones(len(seismogram))
        window = calc_window_data(nsamples * 2)
        if left is True:
            taper_data[:nsamples] = window[:nsamples]
        if right is True:
            taper_data[-nsamples:] = window[-nsamples:]
        seismogram.data *= taper_data

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

    Parameters:
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
    taper_width: timedelta | float,
    taper_method: Literal[
        "bartlett", "blackman", "hamming", "hanning", "kaiser"
    ] = "hanning",
    beta: float = 14.0,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def window[T: Seismogram](
    seismogram: T,
    window_begin_time: datetime,
    window_end_time: datetime,
    taper_width: timedelta | float,
    taper_method: Literal[
        "bartlett", "blackman", "hamming", "hanning", "kaiser"
    ] = "hanning",
    beta: float = 14.0,
    *,
    clone: Literal[True],
) -> T: ...


def window[T: Seismogram](
    seismogram: T,
    window_begin_time: datetime,
    window_end_time: datetime,
    taper_width: timedelta | float,
    taper_method: Literal[
        "bartlett", "blackman", "hamming", "hanning", "kaiser"
    ] = "hanning",
    beta: float = 14.0,
    clone: bool = False,
) -> None | T:
    """Returns a tapered window of a seismogram.

    This function combines the [`crop`][pysmo.functions.crop],
    [`detrend`][pysmo.functions.detrend], [`taper`][pysmo.functions.taper],
    and [`pad`][pysmo.functions.pad] functions to return a 'windowed'
    seismogram. Note that the window *includes* the tapered sections, and
    should thus be defined accordingly.

    Parameters:
        seismogram: Seismogram object.
        window_begin_time: Begin time of the window.
        window_end_time: End time of the window.
        taper_width: With of the taper to use (see [`taper`][pysmo.functions.taper]).
        taper_method: Taper method to use (see [`taper`][pysmo.functions.taper]).
        beta: beta value for the Kaiser window function (ignored for other methods).
        clone: Operate on a clone of the input seismogram.

    Returns:
        Windowed [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        This examples applies a window starting at 100 seconds with a total
        with of 2000 seconds and a taper width of 500 seconds:

        ```python
        >>> from pysmo.functions import window, detrend
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.plotutils import plotseis
        >>> from datetime import timedelta
        >>>
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> taper_width = timedelta(seconds=500)
        >>> window_begin_time = sac_seis.begin_time + timedelta(seconds=100)
        >>> window_end_time = window_begin_time + timedelta(seconds=2000)
        >>> windowed_seis = window(sac_seis, window_begin_time, window_end_time, taper_width, clone=True)
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
        ![Functions window](../../../examples/figures/functions_window.png#only-light){ loading=lazy }
        ![Functions window](../../../examples/figures/functions_window-dark.png#only-dark){ loading=lazy }
        </figure>
    """

    begin_time, end_time = seismogram.begin_time, seismogram.end_time

    if clone is True:
        seismogram = crop(seismogram, window_begin_time, window_end_time, clone=True)
    else:
        crop(seismogram, window_begin_time, window_end_time)
    detrend(seismogram)
    taper(seismogram, taper_width, taper_method, beta)
    pad(seismogram, begin_time, end_time)

    if clone is True:
        return seismogram
    return None
