from pysmo import Seismogram
from typing import Literal, overload
from ._registry import _FILTER_REGISTRY

# NOTE: update this when new filters are added and decorated with @register_filter
type FilterName = Literal[
    "envelope", "gauss", "bandpass", "bandstop", "lowpass", "highpass"
]

__all__ = ["filter"]


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

    Args:
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

    try:
        filter_func = _FILTER_REGISTRY[filter_name]
    except KeyError:
        # This fallback handles cases where FilterName is updated but
        # the function isn't decorated yet.
        valid_filters = ", ".join(_FILTER_REGISTRY.keys())
        raise ValueError(
            f"Filter '{filter_name}' is not registered. Available: {valid_filters}"
        )

    if clone:
        return filter_func(seismogram, clone=True, **filter_options)
    filter_func(seismogram, clone=False, **filter_options)
    return None
