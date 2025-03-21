from ._location import Location, MiniLocation
from typing import Protocol, runtime_checkable
from attrs import define, field, validators
from attrs_strict import type_validator

__all__ = ["Station", "MiniStation"]


@runtime_checkable
class Station(Location, Protocol):
    """The `Station` class defines a protocol for seismic stations in Pysmo.

    Attributes:
        name: Station name or identifier.
        network: Network nam or identifiere.
        latitude (float): Station latitude in degrees.
        longitude (float): Station longitude in degrees.
        elevation: Station elevation in metres.
    """

    @property
    def name(self) -> str: ...

    @name.setter
    def name(self, value: str) -> None: ...

    @property
    def network(self) -> str | None: ...

    @network.setter
    def network(self, value: str) -> None: ...

    @property
    def elevation(self) -> float | None: ...

    @elevation.setter
    def elevation(self, value: float) -> None: ...


@define(kw_only=True)
class MiniStation(MiniLocation):
    """Minimal class for seismic stations.

    The `MiniStation` class provides a minimal implementation of class that
    is compatible with the `Station` type. The class is a subclass of
    `MiniLocation`, and therefore also matches the `Location` type.

    Attributes:
        name: Station name.
        network: Network name.
        elevation: Station elevation.
        longitude (float): Station longitude.
        latitude (float): Station latitude.

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
    network: str | None = field(default=None, validator=type_validator())
    elevation: float | int | None = field(
        default=None,
        validator=validators.optional(
            [validators.gt(-180), validators.le(180), type_validator()]
        ),
    )
