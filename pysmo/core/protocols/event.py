from typing import Protocol
import numpy as np
import datetime


class Event(Protocol):
    """The :class:`Event` class defines a protocol for seismic events in pysmo.
    """
    @property
    def event_latitude(self) -> float:
        """Gets the event latitude."""
        pass

    @event_latitude.setter
    def event_latitude(self, value: float) -> None:
        """Sets the event latitude."""
        pass

    @property
    def event_longitude(self) -> float:
        """Gets the event longitude."""
        pass

    @event_longitude.setter
    def event_longitude(self, value: float) -> None:
        """Sets the event longitude."""
        pass

    @property
    def event_depth(self) -> float:
        """Gets the event depth."""
        pass

    @event_depth.setter
    def event_depth(self, value: float) -> None:
        """Sets the event depth."""
        pass
