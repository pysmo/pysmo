from typing import Protocol, runtime_checkable

from attrs import converters, define, field, setters, validators

from .location import Location

__all__ = ["MiniStation", "MiniStationCode", "Station", "StationCode"]

# --8<-- [start:station-protocol]


@runtime_checkable
class StationCode(Protocol):
    """Protocol class to define the `StationCode` type.

    Network/station/location/channel (NSLC) identity for a data stream,
    independent of geographic location — the subset of `Station` a format
    like miniSEED can provide without coordinates.
    """

    name: str
    """Station name or identifier.

    A 1-5 character identifier for the station recording the data.
    """

    network: str
    """Network name or identifier.

    A 1-2 character code identifying the network/owner of the data.
    """

    location: str
    """Location ID.

    A two character code used to uniquely identify different data streams
    at a single station.
    """

    channel: str
    """Channel code.

    A three character combination used to identify:

    1. Band and general sample rate.
    2. Instrument type.
    3. Orientation of the sensor.
    """


@runtime_checkable
class Station(Location, StationCode, Protocol):
    """Protocol class to define the `Station` type."""

    elevation: int | float | None
    """Station elevation in metres."""


# --8<-- [end:station-protocol]


def _pad_string(x: str) -> str:
    return f"{x:>2}"


@define(kw_only=True)
class MiniStationCode:
    """Minimal class for use with the [`StationCode`][pysmo.StationCode] type.

    Examples:
        ```python
        >>> from pysmo import MiniStationCode, StationCode
        >>> code = MiniStationCode(name="CACB", network="BL", channel="BHZ", location="00")
        >>> isinstance(code, StationCode)
        True
        >>>
        ```
    """

    name: str = field(
        validator=[validators.min_len(1), validators.max_len(5)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Station name.

    See [`StationCode.name`][pysmo.StationCode.name] for more details.
    """

    network: str = field(
        validator=[validators.min_len(1), validators.max_len(2)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Network name.

    See [`StationCode.network`][pysmo.StationCode.network] for more details.
    """

    location: str = field(
        default="  ",
        validator=[validators.min_len(2), validators.max_len(2)],
        converter=_pad_string,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Location ID.

    See [`StationCode.location`][pysmo.StationCode.location] for more details.
    """

    channel: str = field(
        validator=[validators.min_len(3), validators.max_len(3)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Channel code.

    See [`StationCode.channel`][pysmo.StationCode.channel] for more details.
    """


@define(kw_only=True)
class MiniStation:
    """Minimal class for use with the [`Station`][pysmo.Station] type.

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

    name: str = field(
        validator=[validators.min_len(1), validators.max_len(5)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Station name.

    See [`Station.name`][pysmo.Station.name] for more details.
    """

    network: str = field(
        validator=[validators.min_len(1), validators.max_len(2)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Network name.

    See [`Station.network`][pysmo.Station.network] for more details.
    """

    location: str = field(
        default="  ",
        validator=[validators.min_len(2), validators.max_len(2)],
        converter=_pad_string,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Location ID.

    See [`Station.location`][pysmo.Station.location] for more details.
    """

    channel: str = field(
        validator=[validators.min_len(3), validators.max_len(3)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Channel code.

    See [`Station.channel`][pysmo.Station.channel] for more details.
    """

    latitude: float = field(
        converter=float,
        validator=[validators.ge(-90), validators.le(90)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Station latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=float,
        validator=[validators.gt(-180), validators.le(180)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Station longitude from -180 to 180 degrees."""

    elevation: float | None = field(
        default=None,
        converter=converters.optional(float),
        validator=validators.optional(validators.instance_of(float)),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Station elevation."""
