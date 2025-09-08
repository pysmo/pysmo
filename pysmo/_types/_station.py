from ._location import Location
from typing import Protocol, runtime_checkable
from attrs import define, field, validators

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
        """Network name or identifier."""
        ...

    @network.setter
    def network(self, value: str) -> None: ...

    @property
    def elevation(self) -> float | None:
        """Station elevation in metres."""
        ...

    @elevation.setter
    def elevation(self, value: float) -> None: ...


@define(kw_only=True, slots=True)
class MiniStation:
    """Minimal class for use with the Station type.

    The `MiniStation` class provides a minimal implementation of class that
    is compatible with the `Station` type.

    Examples:
        ```python
        >>> from pysmo import MiniStation, Station, Location
        >>> station = MiniStation(latitude=-21.680301, longitude=-46.732601, name="CACB", network="BL")
        >>> isinstance(station, Station)
        True
        >>> isinstance(station, Location)
        True
        >>>
        ```
    """

    name: str
    """Station name."""

    network: str | None = None
    """Network name."""

    latitude: float = field(validator=[validators.ge(-90), validators.le(90)])
    """Station latitude from -90 to 90 degrees."""

    longitude: float = field(validator=[validators.gt(-180), validators.le(180)])
    """Station longitude from -180 to 180 degrees."""

    elevation: float | None = field(
        default=None,
        validator=validators.optional([validators.gt(-180), validators.le(180)]),
    )
    """Station elevation."""
