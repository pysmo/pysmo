import statistics
from collections.abc import Sequence
from copy import deepcopy
from itertools import pairwise
from math import floor
from typing import TYPE_CHECKING, Any, Literal, cast, overload

import numpy as np
import pandas as pd
import scipy.signal

from pysmo import Seismogram
from pysmo.typing import (
    NonNegativeNumber,
    NonNegativeTimedelta,
    PositiveTimedelta,
    UnitFloat,
)

if TYPE_CHECKING:
    from numpy.lib._arraypad_impl import _ModeFunc, _ModeKind

__all__ = [
    "crop",
    "detrend",
    "estimate_delta",
    "merge",
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
    begin_time: pd.Timestamp,
    end_time: pd.Timestamp,
    clone: Literal[False] = ...,
) -> None: ...
@overload
def crop[T: Seismogram](
    seismogram: T,
    begin_time: pd.Timestamp,
    end_time: pd.Timestamp,
    clone: Literal[True],
) -> T: ...


def crop[T: Seismogram](
    seismogram: T, begin_time: pd.Timestamp, end_time: pd.Timestamp, clone: bool = False
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
        >>> import pandas as pd
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> new_begin_time = sac_seis.begin_time + pd.Timedelta(seconds=10)
        >>> new_end_time = sac_seis.end_time - pd.Timedelta(seconds=10)
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

    return seismogram if clone is True else None


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
        >>> 0 == pytest.approx(np.mean(sac_seis.data), abs=1e-8)
        np.False_
        >>> detrend(sac_seis)
        >>> 0 == pytest.approx(np.mean(sac_seis.data), abs=1e-8)
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
    t1: pd.Timestamp | None = ...,
    t2: pd.Timestamp | None = ...,
    clone: Literal[False] = ...,
) -> None: ...
@overload
def normalize[T: Seismogram](
    seismogram: T,
    t1: pd.Timestamp | None = ...,
    t2: pd.Timestamp | None = ...,
    *,
    clone: Literal[True],
) -> T: ...


def normalize[T: Seismogram](
    seismogram: T,
    t1: pd.Timestamp | None = None,
    t2: pd.Timestamp | None = None,
    clone: bool = False,
) -> None | T:
    """Normalise a seismogram with its absolute max value.

    Args:
        seismogram: Seismogram object.
        t1: Start of the window used to find the maximum. If `None`, the search
            starts from the beginning of the seismogram.
        t2: End of the window used to find the maximum. If `None`, the search
            continues to the end of the seismogram.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Normalised [`Seismogram`][pysmo.Seismogram] object if `clone=True`.

    Raises:
        ValueError: If the absolute maximum of the data (within the optional
            time window) is zero, as normalisation would produce undefined results.

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

    start_index, end_index = None, None

    if t1 is not None:
        start_index = time2index(seismogram, t1)

    if t2 is not None:
        end_index = time2index(seismogram, t2)

    abs_max = np.max(np.abs(seismogram.data[start_index:end_index]))
    if abs_max == 0:
        raise ValueError(
            "Cannot normalise a seismogram because the absolute maximum "
            "within the selected time window (or entire trace if no window "
            "is given) is zero."
        )

    if clone is True:
        seismogram = deepcopy(seismogram)

    seismogram.data /= abs_max

    if clone is True:
        return seismogram

    return None


@overload
def pad[T: Seismogram](
    seismogram: T,
    begin_time: pd.Timestamp,
    end_time: pd.Timestamp,
    mode: "_ModeKind | _ModeFunc" = "constant",
    *,
    clone: Literal[True],
    **kwargs: Any,
) -> T: ...


@overload
def pad(
    seismogram: Seismogram,
    begin_time: pd.Timestamp,
    end_time: pd.Timestamp,
    mode: "_ModeKind | _ModeFunc" = "constant",
    clone: Literal[False] = False,
    **kwargs: Any,
) -> None: ...


def pad[T: Seismogram](
    seismogram: T,
    begin_time: pd.Timestamp,
    end_time: pd.Timestamp,
    mode: "_ModeKind | _ModeFunc" = "constant",
    clone: bool = False,
    **kwargs: Any,
) -> None | T:
    """Pad seismogram data.

    This function calculates the indices corresponding to the provided new
    begin and end times using [`time2index`][pysmo.functions.time2index], then
    pads the [`data`][pysmo.Seismogram.data] array using [`numpy.pad`][] and
    updates the [`begin_time`][pysmo.Seismogram.begin_time]. Note that the
    actual begin and end times are set by indexing, so they may be slightly
    different than the provided input begin and end times.

    Args:
        seismogram: [`Seismogram`][pysmo.Seismogram] object.
        begin_time: New begin time.
        end_time: New end time.
        mode: Pad mode to use (see [`numpy.pad`][] for all modes).
        clone: Operate on a clone of the input seismogram.
        kwargs: Keyword arguments to pass to [`numpy.pad`][].

    Returns:
        Padded [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Raises:
        ValueError: If new begin time is after new end time.

    Examples:
        ```python
        >>> from pysmo.functions import pad
        >>> from pysmo.classes import SAC
        >>> import pandas as pd
        >>> import numpy as np
        >>>
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> original_length = len(sac_seis.data)
        >>> sac_seis.data
        array([-47201., -47361., -47511., ..., -82144., -71072., -59960.],
              shape=(57465,))
        >>> new_begin_time = sac_seis.begin_time - pd.Timedelta(seconds=10)
        >>> new_end_time = sac_seis.end_time + pd.Timedelta(seconds=10)
        >>> pad(sac_seis, new_begin_time, new_end_time)
        >>> np.isclose(len(sac_seis.data), original_length + 20 / sac_seis.delta.total_seconds())
        np.True_
        >>> sac_seis.data
        array([0., 0., 0., ..., 0., 0., 0.], shape=(57865,))
        >>>
        ```
    """

    if begin_time > end_time:
        raise ValueError("New begin_time cannot be after new end_time")

    start_index = time2index(seismogram, begin_time, allow_out_of_bounds=True)
    end_index = time2index(seismogram, end_time, allow_out_of_bounds=True)

    if clone is True:
        seismogram = deepcopy(seismogram)

    pad_before = max(0, -start_index)
    pad_after = max(0, end_index - (len(seismogram.data) - 1))

    if pad_before > 0 or pad_after > 0:
        seismogram.data = np.pad(
            seismogram.data,
            pad_width=(pad_before, pad_after),
            mode=mode,
            **kwargs,
        )
        seismogram.begin_time += seismogram.delta * min(0, start_index)

    return seismogram if clone else None


@overload
def resample(
    seismogram: Seismogram, delta: PositiveTimedelta, clone: Literal[False] = ...
) -> None: ...


@overload
def resample[T: Seismogram](
    seismogram: T, delta: PositiveTimedelta, clone: Literal[True]
) -> T: ...


def resample[T: Seismogram](
    seismogram: T, delta: PositiveTimedelta, clone: bool = False
) -> None | T:
    """Resample Seismogram data using the Fourier method.

    This function uses [`scipy.signal.resample`][] to resample the data to a
    new sampling interval. If the new sampling interval is identical to the
    current one, no action is taken.

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
        >>> len(sac_seis.data)
        57465
        >>> original_delta = sac_seis.delta
        >>> new_delta = original_delta * 2
        >>> resample(sac_seis, new_delta)
        >>> len(sac_seis.data)
        28732
        >>>
        ```
    """
    if clone is True:
        seismogram = deepcopy(seismogram)

    if delta != seismogram.delta:
        npts = int(len(seismogram.data) * seismogram.delta / delta)
        seismogram.data = scipy.signal.resample(seismogram.data, npts)
        seismogram.delta = delta

    if clone is True:
        return seismogram
    return None


def estimate_delta(deltas: Sequence[PositiveTimedelta]) -> PositiveTimedelta:
    """Estimate a canonical sampling interval from a set of near-equal deltas.

    Useful when several seismograms nominally share a sampling interval but
    report values that differ only by measurement noise (e.g. clock drift
    reflected in a reported sample rate) or floating-point noise. Returns the low
    median of `deltas`: an order-independent choice that is always one of
    the input values, rather than a synthetic average that none of the
    seismograms actually have.

    This does not check how close the given deltas are to each other; for a
    set of genuinely different sampling intervals it simply returns the low
    median of the sorted values.

    Args:
        deltas: Sampling intervals to estimate a canonical value from.

    Returns:
        The estimated canonical sampling interval.

    Raises:
        ValueError: If `deltas` is empty.

    Examples:
        ```python
        >>> import pandas as pd
        >>> from pysmo.functions import estimate_delta
        >>> deltas = [
        ...     pd.Timedelta(seconds=0.01),
        ...     pd.Timedelta(seconds=0.010000000000001),
        ...     pd.Timedelta(seconds=0.01),
        ... ]
        >>> estimate_delta(deltas)
        Timedelta('0 days 00:00:00.010000')
        >>>
        ```
    """
    if not deltas:
        raise ValueError("No deltas to estimate from.")
    return statistics.median_low(deltas)


@overload
def merge(
    seismograms: Sequence[Seismogram],
    *,
    delta: PositiveTimedelta | None = ...,
    auto_delta: Literal[False] = ...,
    gap_tolerance_factor: NonNegativeNumber = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def merge(
    seismograms: Sequence[Seismogram],
    *,
    delta: None = ...,
    auto_delta: Literal[True],
    gap_tolerance_factor: NonNegativeNumber = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def merge[T: Seismogram](
    seismograms: Sequence[T],
    *,
    delta: PositiveTimedelta | None = ...,
    auto_delta: Literal[False] = ...,
    gap_tolerance_factor: NonNegativeNumber = ...,
    clone: Literal[True],
) -> T: ...


@overload
def merge[T: Seismogram](
    seismograms: Sequence[T],
    *,
    delta: None = ...,
    auto_delta: Literal[True],
    gap_tolerance_factor: NonNegativeNumber = ...,
    clone: Literal[True],
) -> T: ...


def merge[T: Seismogram](
    seismograms: Sequence[Seismogram],
    *,
    delta: PositiveTimedelta | None = None,
    auto_delta: bool = False,
    gap_tolerance_factor: NonNegativeNumber = 0.5,
    clone: bool = False,
) -> None | T:
    """Merge contiguous seismograms into a single seismogram.

    Empty seismograms take no part in the merge arithmetic (they never
    contribute data and never constrain sampling-interval or gap/overlap
    checks) and are absent from the result if there are non-empty
    seismograms to merge with. The remaining, non-empty seismograms are
    merged in chronological order of `begin_time`, regardless of the order
    they are given in, and must lie on a single regular sampling grid. By
    default, this requires equal sampling intervals; when `delta` is
    provided, each non-empty seismogram is first resampled to that common
    interval using [`resample`][pysmo.functions.resample]. If `delta` is
    `None` and `auto_delta` is `True`, a common interval is estimated with
    [`estimate_delta`][pysmo.functions.estimate_delta] instead of requiring
    an exact match — useful when sampling intervals only disagree by
    measurement or floating-point noise.

    A small amount of boundary timestamp jitter is allowed, bounded by
    `gap_tolerance_factor` sampling intervals, so metadata rounding noise does
    not block otherwise valid merges. If consecutive seismograms overlap
    within this tolerance, the overlapping samples must match (compared with
    [`allclose`][numpy.allclose] and its default tolerances, to accommodate
    floating-point noise from e.g. prior resampling); they are verified and
    the duplicates are discarded rather than concatenated.

    When `clone=False`, the first seismogram in `seismograms` (as given —
    not necessarily the chronologically first, and regardless of whether it
    is itself empty) is modified in place and becomes the merged result: its
    `begin_time` and `data` are overwritten to reflect the full,
    chronologically-ordered merge of the non-empty seismograms. Other input
    seismograms are never modified.

    Args:
        seismograms: Seismograms to merge. May be given in any order; any mix
            of types satisfying the [`Seismogram`][pysmo.Seismogram] protocol
            works at runtime. When `clone=True`, the return type is inferred
            from `seismograms`; for a bare list/tuple literal mixing concrete
            types, annotate it as `Sequence[Seismogram]` to keep the call
            type-checked (see Examples).
        delta: Sampling interval to resample all non-empty seismograms to
            before merging. If `None`, all non-empty input seismograms must
            already share the same sampling interval, unless `auto_delta`
            is `True`.
        auto_delta: Estimate a common sampling interval from the non-empty
            seismograms with
            [`estimate_delta`][pysmo.functions.estimate_delta] instead of
            requiring an exact match. Mutually exclusive with `delta`; type
            checkers reject passing both.
        gap_tolerance_factor: Maximum allowed boundary timestamp jitter between
            consecutive seismograms, as a fraction of the sampling interval.
        clone: Operate on a clone of the first input seismogram.

    Returns:
        Merged [`Seismogram`][pysmo.Seismogram] object if called with
        `clone=True`.

    Raises:
        ValueError: If `seismograms` is empty, contains no non-empty
            seismograms, the sampling intervals of the non-empty seismograms
            differ and neither `delta` nor `auto_delta` is provided, the
            boundary between consecutive non-empty seismograms contains a
            gap or overlap exceeding the allowed tolerance, overlapping
            samples do not match, or `gap_tolerance_factor` is negative.

    Examples:
        ```python
        >>> import numpy as np
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.functions import merge
        >>> first = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        ...     delta=pd.Timedelta(seconds=1),
        ...     data=np.array([1.0, 2.0, 3.0]),
        ... )
        >>> second = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        ...     delta=pd.Timedelta(seconds=1),
        ...     data=np.array([4.0, 5.0]),
        ... )
        >>> merged = merge([first, second], clone=True)
        >>> merged.data
        array([1., 2., 3., 4., 5.])
        >>> merged.begin_time
        Timestamp('2010-02-27 06:30:00+0000', tz='UTC')

        ```

        Merging seismograms of different concrete types works the same way
        at runtime. A bare list literal's inferred type comes from its
        elements, though, and for a mix of concrete types that inferred type
        may not satisfy the `Seismogram` bound at all, making the call fail
        to type-check. Annotate the list as `Sequence[Seismogram]` to keep
        the result type-checked:

        ```python
        >>> from collections.abc import Sequence
        >>> from pysmo import Seismogram
        >>> from pysmo.classes import GeoCsvSeismogram
        >>> geocsv_seis = GeoCsvSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:05Z"),
        ...     delta=pd.Timedelta(seconds=1),
        ...     data=np.array([6.0, 7.0]),
        ...     sid="IU_ANMO_00_LHZ",
        ... )
        >>> mixed: Sequence[Seismogram] = [merged, geocsv_seis]
        >>> merged_mixed = merge(mixed, clone=True)
        >>> merged_mixed.data
        array([1., 2., 3., 4., 5., 6., 7.])
        >>>
        ```

        The merged object's actual class is always `seismograms[0]`'s class,
        regardless of what a type checker can infer — this is purely a
        static-typing concern. If downstream code depends on the concrete
        type, merging a single concrete type (the common case) lets it be inferred
        automatically, without needing the annotation above.

        Seismograms whose sampling intervals only disagree by measurement or
        floating-point noise (see
        [`estimate_delta`][pysmo.functions.estimate_delta]) can be merged
        with `auto_delta=True` instead of requiring an exact match:

        ```python
        >>> steady = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        ...     delta=pd.Timedelta(seconds=1),
        ...     data=np.array([1.0, 2.0, 3.0]),
        ... )
        >>> jittery = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        ...     delta=pd.Timedelta(seconds=1) + pd.Timedelta(nanoseconds=1),
        ...     data=np.array([4.0, 5.0, 6.0]),
        ... )
        >>> auto_merged = merge(
        ...     [steady, jittery], auto_delta=True, clone=True
        ... )
        >>> auto_merged.delta
        Timedelta('0 days 00:00:01')
        >>> auto_merged.data
        array([1., 2., 3., 4., 5., 6.])
        >>>
        ```

        `auto_delta` estimates a canonical interval with
        [`estimate_delta`][pysmo.functions.estimate_delta]; it does not
        verify that the seismograms genuinely belong on the same sampling
        grid. Users are encouraged to inspect the resulting `delta` (as
        above), or call
        [`estimate_delta`][pysmo.functions.estimate_delta] directly
        beforehand, to confirm the estimate is the value expected rather
        than assuming it silently.
    """
    if gap_tolerance_factor < 0:
        raise ValueError("gap_tolerance_factor must be non-negative.")

    if not seismograms:
        raise ValueError("No seismograms to merge.")

    working = (
        [deepcopy(seismogram) for seismogram in seismograms]
        if clone
        else list(seismograms)
    )

    non_empty = [seismogram for seismogram in working if len(seismogram.data)]
    if not non_empty:
        raise ValueError("No non-empty seismograms to merge.")

    if delta is None and auto_delta:
        delta = estimate_delta([seismogram.delta for seismogram in non_empty])

    if delta is None:
        reference_delta = non_empty[0].delta
        for seismogram in non_empty[1:]:
            if seismogram.delta != reference_delta:
                raise ValueError(
                    "Cannot merge seismograms with different sampling intervals "
                    f"without resampling: {reference_delta} vs {seismogram.delta}."
                )
    else:
        reference_delta = delta
        for index, seismogram in enumerate(working):
            if len(seismogram.data) == 0:
                continue
            if seismogram.delta == delta:
                continue
            if clone or index > 0:
                working[index] = resample(seismogram, delta, clone=True)
            else:
                resample(seismogram, delta)
        non_empty = [seismogram for seismogram in working if len(seismogram.data)]

    ordered = sorted(non_empty, key=lambda seismogram: seismogram.begin_time)

    overlap_samples = [0] * len(ordered)
    for index, (prev, curr) in enumerate(pairwise(ordered), start=1):
        expected_next = prev.end_time + prev.delta
        gap = curr.begin_time - expected_next
        tolerance = prev.delta * gap_tolerance_factor
        if abs(gap) > tolerance:
            description = (
                f"gap of {gap.total_seconds():.6f} s"
                if gap > pd.Timedelta(0)
                else f"overlap of {-gap.total_seconds():.6f} s"
            )
            raise ValueError(
                f"Data {description} detected between seismogram ending at "
                f"{prev.end_time} and seismogram starting at {curr.begin_time}."
            )
        if gap < pd.Timedelta(0):
            samples = min(round(-gap / prev.delta), len(prev.data), len(curr.data))
            if samples > 0 and not np.allclose(
                prev.data[-samples:], curr.data[:samples]
            ):
                raise ValueError(
                    f"Overlapping samples between seismogram ending at "
                    f"{prev.end_time} and seismogram starting at "
                    f"{curr.begin_time} do not match; cannot merge."
                )
            overlap_samples[index] = samples

    merged = cast(T, working[0])
    merged.begin_time = ordered[0].begin_time
    merged.delta = reference_delta
    merged.data = np.concatenate(
        [ordered[0].data]
        + [
            seismogram.data[samples:]
            for seismogram, samples in zip(ordered[1:], overlap_samples[1:])
        ]
    )

    if clone:
        return merged
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


def taper[T: Seismogram](
    seismogram: T,
    taper_width: NonNegativeTimedelta | UnitFloat,
    window_type: _WindowType = "hann",
    clone: bool = False,
) -> None | T:
    """Apply a symmetric taper to the ends of a Seismogram.

    The taper width is understood as the portion of the seismogram affected
    by the taper window function. It can be provided as an absolute duration
    (non-negative [`Timedelta`][pandas.Timedelta]), or as a fraction of
    seismogram length ([`float`][] between `0` and `1`). Internally, absolute
    durations are converted to fractions by dividing by the total seismogram
    duration, and absolute durations should therefore not exceed the total
    seismogram duration.

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

    Note:
        If `taper_width` resolves to fewer than 2 samples, no taper is applied.
        This can occur when a very small [`Timedelta`][pandas.Timedelta] is
        provided.

    Examples:
        ```python
        >>> from pysmo.functions import taper, detrend
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> detrend(sac_seis)
        >>> sac_seis.data
        array([   821.53861155,    661.55931267,    511.58001379, ...,
               -32931.93353333, -21859.9128322 , -10747.89213108], shape=(57465,))
        >>> taper(sac_seis, 0.2)
        >>> sac_seis.data
        array([ 0.00000000e+00,  4.94398663e-05,  1.52926246e-04, ...,
               -9.84431924e-03, -1.63364213e-03, -0.00000000e+00], shape=(57465,))
        >>>
        ```
    """

    nsamples: int
    if isinstance(taper_width, pd.Timedelta):
        nsamples = taper_width // seismogram.delta
    else:
        nsamples = floor(len(seismogram.data) * taper_width)

    if nsamples > len(seismogram.data):
        raise ValueError(
            "'taper_width' is too large. Total taper width exceeds the duration of the seismogram."
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
    time: pd.Timestamp,
    allow_out_of_bounds: bool = False,
) -> int:
    """
    Converts a specific timestamp to the corresponding data array index.

    Seismic data is sampled at discrete intervals. When a requested time does
    not align perfectly with a sample, this function selects the nearest
    index using the following rules:

    1. If the time is within 0.1% of a sample interval of an integer, it
       "snaps" to that integer to account for floating-point jitter.
    2. Use standard rounding (0.5 rounds up to the next index) otherwise.

    Args:
        seismogram: Seismogram object.
        time: The absolute time to convert.
        allow_out_of_bounds: If True, returns the calculated index even if it
            falls outside the seismogram's data range [0, len-1].

    Returns:
        The index of the sample closest to the provided time.

    Raises:
        ValueError: If the calculated index is outside the data array and
            `allow_out_of_bounds` is False.
    """
    # Calculate the fractional index position
    index_float = (time - seismogram.begin_time) / seismogram.delta

    # Snap to nearest integer if within a tiny tolerance (1e-3 samples)
    # This prevents 2.999999999 from being floored to 2 instead of 3.
    if np.isclose(index_float, np.round(index_float), atol=1e-3):
        index = int(np.round(index_float))
    # Standard rounding within the trace (0.5 rounds up)
    else:
        index = int(np.floor(index_float + 0.5))

    # Validation
    if 0 <= index < len(seismogram.data) or allow_out_of_bounds:
        return index

    raise ValueError(
        f"Calculated index {index} is out of bounds for seismogram with "
        f"{len(seismogram.data)} samples. (Target time: {time})"
    )


@overload
def window(
    seismogram: Seismogram,
    window_begin_time: pd.Timestamp,
    window_end_time: pd.Timestamp,
    ramp_width: NonNegativeTimedelta | NonNegativeNumber,
    window_type: _WindowType = ...,
    same_shape: bool = False,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def window[T: Seismogram](
    seismogram: T,
    window_begin_time: pd.Timestamp,
    window_end_time: pd.Timestamp,
    ramp_width: NonNegativeTimedelta | NonNegativeNumber,
    window_type: _WindowType = ...,
    *,
    same_shape: bool = False,
    clone: Literal[True],
) -> T: ...


def window[T: Seismogram](
    seismogram: T,
    window_begin_time: pd.Timestamp,
    window_end_time: pd.Timestamp,
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
            - If `pd.Timedelta`: used as absolute duration.

            Note: Total duration = window length + (2 * `ramp_width`).
        window_type: Taper method to use (see [`taper`][pysmo.functions.taper]).
        same_shape: If True, pad the seismogram to its original length after
            windowing.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Windowed [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Raises:
        ValueError: If the ramp extends beyond the seismogram on either side.

    Examples:
        In this example we focus on a window starting 600 seconds after the
        `begin_time` of the seismogram and lasting for 1200 seconds. Setting the
        `ramp_width` to 300 seconds means that the actual window will start 300
        seconds earlier and end 300 seconds later than the specified window
        begin and end times.

        ```python
        >>> from pysmo.functions import window, detrend
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.plotutils import plotseis
        >>> import pandas as pd
        >>>
        >>> sac_seis = SAC.from_file("example.sac").seismogram
        >>> ramp_width = pd.Timedelta(seconds=300)
        >>> window_begin_time = sac_seis.begin_time + pd.Timedelta(seconds=600)
        >>> window_end_time = window_begin_time + pd.Timedelta(seconds=1200)
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
        ![Functions window](../../images/sybil/functions_window.png#only-light){ loading=lazy }
        ![Functions window](../../images/sybil/functions_window-dark.png#only-dark){ loading=lazy }
        </figure>
    """

    begin_time, end_time = seismogram.begin_time, seismogram.end_time

    window_duration = window_end_time - window_begin_time
    ramp_duration = (
        ramp_width
        if isinstance(ramp_width, pd.Timedelta)
        else ramp_width * window_duration  # ty: ignore[unsupported-operator]
    )

    if window_begin_time - ramp_duration < seismogram.begin_time:
        raise ValueError(
            f"ramp_width={ramp_width} requires data before {window_begin_time - ramp_duration}, "
            f"but seismogram only starts at {seismogram.begin_time}."
        )
    if window_end_time + ramp_duration > seismogram.end_time:
        raise ValueError(
            f"ramp_width={ramp_width} requires data after {window_end_time + ramp_duration}, "
            f"but seismogram only ends at {seismogram.end_time}."
        )

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
