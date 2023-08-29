from pysmo import Location
from typing import Protocol, runtime_checkable


# Option 1
@runtime_checkable
class StationEvent(Protocol):

    @property
    def stat_coords(self) -> Location:
        ...

    @stat_coords.setter
    def stat_coords(self, value: Location) -> None:
        ...

    @property
    def eve_coords(self) -> Location:
        ...

    @eve_coords.setter
    def eve_coords(self, value: Location) -> None:
        ...


# Option 2
@runtime_checkable
class StationDistAzi(Protocol):

    @property
    def stat_coords(self) -> Location:
        ...

    @stat_coords.setter
    def stat_coords(self, value: Location) -> None:
        ...

    @property
    def distance(self) -> float:
        ...

    @distance.setter
    def distance(self, value: float) -> None:
        ...

    @property
    def azimuth(self) -> float:
        ...

    @azimuth.setter
    def azimuth(self, value: float) -> None:
        ...
