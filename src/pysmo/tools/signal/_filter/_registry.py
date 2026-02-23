from typing import Any, Callable, Protocol, overload, Literal
from pysmo import Seismogram


class SeismogramFilter(Protocol):
    """Protocol defining the expected signature for all filter functions."""

    @overload
    def __call__(
        self,
        seismogram: Seismogram,
        *args: Any,
        clone: Literal[False] = ...,
        **kwargs: Any,
    ) -> None: ...

    @overload
    def __call__[T: Seismogram](
        self,
        seismogram: T,
        *args: Any,
        clone: Literal[True],
        **kwargs: Any,
    ) -> T: ...

    def __call__(
        self,
        seismogram: Seismogram,
        *args: Any,
        clone: bool = False,
        **kwargs: Any,
    ) -> Seismogram | None: ...


type FilterRegistry = dict[str, SeismogramFilter]
_FILTER_REGISTRY: FilterRegistry = {}


def register_filter[F: Callable[..., Any]](func: F) -> F:
    """
    Decorator to mark and register valid filter functions.

    Registered functions are added to the `_FILTER_REGISTRY` and become available
    for use through the `pysmo.tools.signal.filter` convenience wrapper.

    Note:
        When adding a new filter, you must also add its name to the `FilterName`
        type alias in `pysmo.tools.signal._filter._filter` to ensure type safety
        and passing registry tests.
    """
    # cast to SeismogramFilter for registry, but return original F for signature preservation
    _FILTER_REGISTRY[func.__name__] = func
    return func
