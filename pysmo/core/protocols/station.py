from typing import Protocol


class Station(Protocol):
    """The :class:`Station` class defines a protocol for seismic stations in Pysmo.
    """
    @property
    def name(self) -> str:
        """Retuns the station name."""
        ...

    @name.setter
    def name(self, value: str) -> None:
        """Sets the station name."""
        ...

    @property
    def station_latitude(self) -> float:
        """Retuns the station latitude."""
        ...

    @station_latitude.setter
    def station_latitude(self, value: float) -> None:
        """Sets the station latitude."""
        ...

    @property
    def station_longitude(self) -> float:
        """Retuns the station longitude."""
        ...

    @station_longitude.setter
    def station_longitude(self, value: float) -> None:
        """Sets the station longitude."""
        ...

    @property
    def station_elevation(self) -> float:
        """Retuns the station elevation."""
        ...

    @station_elevation.setter
    def station_elevation(self, value: float) -> None:
        """Sets the station elevation."""
        ...
