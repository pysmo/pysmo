from ._location import Location, MiniLocation
from typing import Protocol, runtime_checkable
from attrs import define, field, validators
from attrs_strict import type_validator

__all__ = ["Station", "MiniStation"]


@runtime_checkable
class Station(Location, Protocol):
    """Protocol class to define the Station type."""

    @property
    def name(self) -> str:
        """Station name or identifier."""
        ...

    @name.setter
    def name(self, value: str) -> None: ...

    @property
    def network(self) -> str | None:
        """Network name or identifiere."""
        ...

    @network.setter
    def network(self, value: str) -> None: ...

    @property
    def elevation(self) -> float | None:
        """Station elevation in metres."""
        ...

    @elevation.setter
    def elevation(self, value: float) -> None: ...


@define(kw_only=True)
class MiniStation(MiniLocation):
    """Minimal class for use with the Station type.

    The `MiniStation` class provides a minimal implementation of class that
    is compatible with the `Station` type. The class is a subclass of
    `MiniLocation`, and therefore also matches the `Location` type.

    Examples:
        >>> from pysmo import MiniStation, Station, Location
        >>> my_station = MiniStation(latitude=-21.680301, longitude=-46.732601,
                                     name="CACB", network="BL")
        >>> isinstance(my_station, Station)
        True
        >>> isinstance(my_station, Location)
        True
    """

    name: str = field(validator=type_validator())
    """Station name."""

    network: str | None = field(default=None, validator=type_validator())
    """Network name."""

    elevation: float | int | None = field(
        default=None,
        validator=validators.optional(
            [validators.gt(-180), validators.le(180), type_validator()]
        ),
    )
    """Station elevation."""
