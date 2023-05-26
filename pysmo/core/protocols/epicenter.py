from typing import Protocol, runtime_checkable


@runtime_checkable
class Epicenter(Protocol):
    """The :class:`Epicenter` defines an epicenter in pysmo.
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
        """Returns the event longitude."""
        ...

    @event_longitude.setter
    def event_longitude(self, value: float) -> None:
        """Sets the event longitude."""
        ...
