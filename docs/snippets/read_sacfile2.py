from pysmo._io import SacIO


class SacIO2(SacIO):
    @property
    def latitude(self) -> float:
        if self.stla is None:  # (1)!
            raise ValueError("SAC Header STLA is not set")
        return self.stla

    @latitude.setter
    def latitude(self, value: float) -> None:
        self.stla = value

    @property
    def longitude(self) -> float:
        if self.stlo is None:
            raise ValueError("SAC Header STLO is not set")
        return self.stlo

    @longitude.setter
    def longitude(self, value: float) -> None:
        self.stlo = value


my_sac2 = SacIO2.from_file("testfile.sac")
