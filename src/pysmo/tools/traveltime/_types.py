"""Type aliases and the backend protocol shared across the travel-time tools."""

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, runtime_checkable

import pandas as pd

type Model = Literal["iasp91", "ak135"]
"""A velocity model included with pysmo."""

type Wave = Literal["P", "S"]
"""The body-wave type a slowness profile is built for."""

type Phase = Literal["P", "S", "PcP", "ScS", "PcS", "ScP"]
"""A phase name the built-in solver computes."""


@runtime_checkable
class TravelTimeBackend(Protocol):
    """The shape of a replacement travel-time function.

    Any callable of the form
    `(*, depth, distance, phases) -> Mapping[str, pd.Timedelta]` qualifies.
    *depth* is in metres (positive down), *distance* in epicentral
    degrees, *phases* a sequence of phase names, not restricted to the
    built-in set. The result maps each phase that has an arrival at the
    given geometry to its travel time, omitting the rest.
    """

    def __call__(
        self, *, depth: float, distance: float, phases: Sequence[str]
    ) -> Mapping[str, pd.Timedelta]:
        """Return travel times for a source–receiver geometry."""
        ...
