from typing import Protocol, runtime_checkable
from pysmo.core.protocols import Epicenter


@runtime_checkable
class Hypocenter(Epicenter, Protocol):
    """The :class:`Hypocenter` class defines a protocol for hypocenters in pysmo.
    """
    @property
    def event_depth(self) -> float:
        """Returns the event depth."""
        ...

    @event_depth.setter
    def event_depth(self, value: float) -> None:
        """Sets the event depth."""
        ...
