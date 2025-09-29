from ._location import Location
from typing import Protocol, runtime_checkable
from attrs import define, field, validators

__all__ = ["Station", "MiniStation"]


@runtime_checkable
class Station(Location, Protocol):
    """Protocol class to define the `Station` type."""

    @property
    def name(self) -> str:
        """Station name or identifier.

        A 1-5 character identifier for the station recording the data.
        """
        ...

    @name.setter
    def name(self, value: str) -> None: ...

    @property
    def network(self) -> str:
        """Network name or identifier.

        A 1-2 character code identifying the network/owner of the data.
        """
        ...

    @network.setter
    def network(self, value: str) -> None: ...

    @property
    def location(self) -> str:
        """Location ID.

        A two character code used to uniquely identify different data streams
        at a single stationa.
        """
        ...

    @location.setter
    def location(self, value: str) -> None: ...

    @property
    def channel(self) -> str:
        """Channel code.

        A three character combination used to identify:

        1. Band and general sample rate.
        2. Instrument type.
        3. Orientation of the sensor.
        """
        ...

    @channel.setter
    def channel(self, value: str) -> None: ...

    @property
    def elevation(self) -> float | None:
        """Station elevation in metres."""
        ...

    @elevation.setter
    def elevation(self, value: float) -> None: ...


def pad_string(x: str) -> str:
    return f"{x:>2}"


@define(kw_only=True, slots=True)
class MiniStation:
    """Minimal class for use with the Station type.

    The `MiniStation` class provides a minimal implementation of class that
    is compatible with the `Station` type.

    Examples:
        ```python
        >>> from pysmo import MiniStation, Station, Location
        >>> station = MiniStation(latitude=-21.680301, longitude=-46.732601, name="CACB", network="BL", channel="BHZ", location="00")
        >>> isinstance(station, Station)
        True
        >>> isinstance(station, Location)
        True
        >>>
        ```
    """

    name: str = field(validator=[validators.min_len(1), validators.max_len(5)])
    """Station name.

    See [`Station.name`][pysmo.Station.name] for more details.
    """

    network: str = field(validator=[validators.min_len(1), validators.max_len(2)])
    """Network name.

    See [`Station.network`][pysmo.Station.network] for more details.
    """

    location: str = field(
        default="  ",
        validator=[validators.min_len(2), validators.max_len(2)],
        converter=pad_string,
    )
    """Location ID.

    See [`Station.location`][pysmo.Station.location] for more details.
    """

    channel: str = field(validator=[validators.min_len(3), validators.max_len(3)])
    """Channel code.
 
    See [`Station.channel`][pysmo.Station.channel] for more details.
    """

    latitude: float = field(validator=[validators.ge(-90), validators.le(90)])
    """Station latitude from -90 to 90 degrees."""

    longitude: float = field(validator=[validators.gt(-180), validators.le(180)])
    """Station longitude from -180 to 180 degrees."""

    elevation: float | None = field(
        default=None, validator=validators.optional(validators.instance_of(float | int))
    )
    """Station elevation."""
