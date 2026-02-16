from pysmo import Seismogram
from typing import Literal, overload, get_args
from ._gauss import envelope, gauss
from ._butter import bandpass, bandstop, lowpass, highpass

__all__ = ["filter"]
__all__ += ["envelope", "gauss"]
__all__ += ["bandpass", "bandstop", "lowpass", "highpass"]

type FilterName = Literal[
    "envelope", "gauss", "bandpass", "bandstop", "lowpass", "highpass"
]


@overload
def filter(
    seismogram: Seismogram,
    filter_name: FilterName,
    clone: Literal[False] = ...,
    **filter_options: float | int | bool,
) -> None: ...


@overload
def filter[T: Seismogram](
    seismogram: T,
    filter_name: FilterName,
    clone: Literal[True],
    **filter_options: float | int | bool,
) -> T: ...


def filter[T: Seismogram](
    seismogram: T,
    filter_name: FilterName,
    clone: bool = False,
    **filter_options: float | int | bool,
) -> T | None:
    """
    Apply a specified filter to the input seismogram.

    This function is a convenience wrapper that calls other filters in this module.

    Parameters:
        seismogram: The input seismogram to be filtered.
        filter_name: The type of filter to apply.
        clone: If True, return a new Seismogram object with the filtered data. If False, modify the input seismogram in place.
        **filter_options: Filter parameters passed to the specified filter function.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import filter
        >>> seis = SAC.from_file("example.sac").seismogram
        >>>
        >>> # create a new filtered seismogram with a lowpass filter
        >>> filtered_seis = filter(seis, "lowpass", freqmax=0.5, clone=True)
        >>>
        >>> # or update in place with a bandpass filter
        >>> filter(seis, "bandpass", freqmin=0.1, freqmax=0.5)
        >>>
        ```
    """
    filters = {name: globals()[name] for name in get_args(FilterName.__value__)}
    try:
        filter_func = filters[filter_name]
    except KeyError:
        raise ValueError(
            f"Unknown filter '{filter_name}'. Must be one of: {', '.join(filters)}."
        )
    return filter_func(seismogram, **filter_options, clone=clone)
