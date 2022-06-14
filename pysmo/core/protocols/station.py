from typing import Protocol


class Station(Protocol):
    """The :class:`Station` class defines a protocol for seismic stations in pysmo.
    """
    @property
    def name(self) -> str:
        """Gets the station name."""
        ...

    @name.setter
    def name(self, value: str) -> None:
        """Sets the station name."""
        ...

    @property
    def station_latitude(self) -> float:
        """Gets the station latitude."""
        ...

    @station_latitude.setter
    def station_latitude(self, value: float) -> None:
        """Sets the station latitude."""
        ...

    @property
    def station_longitude(self) -> float:
        """Gets the station longitude."""
        ...

    @station_longitude.setter
    def station_longitude(self, value: float) -> None:
        """Sets the station longitude."""
        ...

    @property
    def station_elevation(self) -> float:
        """Gets the station elevation."""
        ...

    @station_elevation.setter
    def station_elevation(self, value: float) -> None:
        """Sets the station elevation."""
        ...
