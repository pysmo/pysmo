from typing import Protocol
import numpy as np
import datetime


class Station(Protocol):
    """The :class:`Station` class defines a protocol for seismic stations in pysmo.
    """
    @property
    def name(self) -> str:
        """Gets the station name."""
        pass

    @name.setter
    def name(self, value: str) -> None:
        """Sets the station name."""
        pass

    @property
    def station_latitude(self) -> float:
        """Gets the station latitude."""
        pass

    @station_latitude.setter
    def station_latitude(self, value: float) -> None:
        """Sets the station latitude."""
        pass

    @property
    def station_longitude(self) -> float:
        """Gets the station longitude."""
        pass

    @station_longitude.setter
    def station_longitude(self, value: float) -> None:
        """Sets the station longitude."""
        pass

    @property
    def station_elevation(self) -> float:
        """Gets the station elevation."""
        pass

    @station_elevation.setter
    def station_elevation(self, value: float) -> None:
        """Sets the station elevation."""
        pass
