from typing import Protocol


class Event(Protocol):
    """The :class:`Event` class defines a protocol for seismic events in Pysmo.
    """
    @property
    def event_latitude(self) -> float:
        """Returns the event latitude."""
        ...

    @event_latitude.setter
    def event_latitude(self, value: float) -> None:
        """Sets the event latitude."""
        ...

    @property
    def event_longitude(self) -> float:
        """Gets the event longitude."""
        ...

    @event_longitude.setter
    def event_longitude(self, value: float) -> None:
        """Sets the event longitude."""
        ...

    @property
    def event_depth(self) -> float:
        """Gets the event depth."""
        ...

    @event_depth.setter
    def event_depth(self, value: float) -> None:
        """Sets the event depth."""
        ...
