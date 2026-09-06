from typing import Literal, overload

from pysmo import Seismogram

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
    *,
    replace: Literal[False] = ...,
    **filter_options: bool | int | float,
) -> None: ...


@overload
def filter[T: Seismogram](
    seismogram: T,
    filter_name: FilterName,
    *,
    replace: Literal[True],
    **filter_options: bool | int | float,
) -> T: ...


def filter[T: Seismogram](
    seismogram: T,
    filter_name: FilterName,
    *,
    replace: bool = False,
    **filter_options: bool | int | float,
) -> T | None:
    """Apply a specified filter to the input seismogram.

    This function is a convenience wrapper that calls other filters in this module.

    Args:
        seismogram: The input seismogram to be filtered.
        filter_name: The type of filter to apply.
        replace: If `True`, return a new Seismogram and leave the input
            untouched. If `False`, modify the input seismogram in place. Not
            supported by every concrete type (see [`pysmo.functions`][]).
        **filter_options: Filter parameters passed to the specified filter
            function.

    Returns:
        A new Seismogram containing the filtered data when called with
        `replace=True`.

    Raises:
        ValueError: If `filter_name` is not a registered filter.

    Examples:
        ```python
        >>> from pysmo.classes import MSeed
        >>> from pysmo.tools.signal import filter
        >>> seis = MSeed.from_file("example.mseed")
        >>>
        >>> # create a new filtered seismogram with a lowpass filter
        >>> filtered_seis = filter(seis, "lowpass", freqmax=0.5, replace=True)
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
        ) from None

    if replace:
        return filter_func(seismogram, replace=True, **filter_options)
    filter_func(seismogram, replace=False, **filter_options)
    return None
