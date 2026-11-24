from typing import Protocol

from attrs import define, field, setters

from pysmo.lib.converters import to_azimuth
from pysmo.lib.validators import is_azimuth, is_dip

__all__ = ["MiniOrientation", "Orientation"]


class Orientation(Protocol):
    """Protocol class to define the `Orientation` type.

    The direction a component records ground motion along, following the
    SEED conventions: motion along this direction gives positive sample
    values. A vertical component pointing up has `dip` -90, a north
    component has `azimuth` 0 and `dip` 0, and an east component has
    `azimuth` 90 and `dip` 0.

    `azimuth` is always in the range [0, 360). Every pysmo implementation
    wraps it into this range. It is the component azimuth, not the
    source–receiver azimuth that [`pysmo.tools.azdist.azimuth`][]
    calculates. At a dip of ±90 the
    azimuth is meaningless, so two vertical orientations can differ in
    azimuth.

    An implementation whose orientation is not set raises
    [`MissingValueError`][pysmo.exceptions.MissingValueError] when either
    attribute is read.
    """

    azimuth: float
    """Azimuth in degrees clockwise from north, from 0 to 360 (exclusive)."""

    dip: float
    """Dip in degrees down from horizontal, from -90 (up) to 90 (down)."""


@define(kw_only=True)
class MiniOrientation:
    """Minimal implementation of the `Orientation` type.

    See [`Orientation`][pysmo.Orientation].

    Examples:
        An azimuth outside [0, 360) is wrapped into it:

        ```python
        >>> from pysmo import MiniOrientation
        >>> orientation = MiniOrientation(azimuth=-90, dip=0)
        >>> orientation.azimuth
        270.0
        >>>
        ```
    """

    azimuth: float = field(
        converter=to_azimuth,
        validator=is_azimuth,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Azimuth in degrees clockwise from north, wrapped into [0, 360)."""

    dip: float = field(
        converter=float,
        validator=is_dip,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Dip in degrees down from horizontal, from -90 to 90."""
