from dataclasses import dataclass


@dataclass
class City:
    name: str
    founded: int
    latitude: float
    longitude: float
    elevation: float
