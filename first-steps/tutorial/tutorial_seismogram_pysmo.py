from dataclasses import dataclass, field
from tutorial_seismogram import TutorialSeismogram


@dataclass
class TutorialStation:
    parent: TutorialSeismogram

    @property
    def latitude(self) -> float:
        if self.parent.station_latitude is None:
            raise ValueError("parent value may not be None")
        return self.parent.station_latitude

    @latitude.setter
    def latitude(self, value: float) -> None:
        self.parent.station_latitude = value

    @property
    def longitude(self) -> float:
        if self.parent.station_longitude is None:
            raise ValueError("parent value may not be None")
        return self.parent.station_longitude

    @longitude.setter
    def longitude(self, value: float) -> None:
        self.parent.station_longitude = value


@dataclass
class TutorialEvent:
    parent: TutorialSeismogram

    @property
    def latitude(self) -> float:
        if self.parent.event_latitude is None:
            raise ValueError("parent value may not be None")
        return self.parent.event_latitude

    @latitude.setter
    def latitude(self, value: float) -> None:
        self.parent.event_latitude = value

    @property
    def longitude(self) -> float:
        if self.parent.event_longitude is None:
            raise ValueError("parent value may not be None")
        return self.parent.event_longitude

    @longitude.setter
    def longitude(self, value: float) -> None:
        self.parent.event_longitude = value


@dataclass
class TutorialSeismogramPysmo(TutorialSeismogram):
    station: TutorialStation = field(init=False)
    event: TutorialEvent = field(init=False)

    def __post_init__(self) -> None:
        self.station = TutorialStation(parent=self)
        self.event = TutorialEvent(parent=self)
