from some_library import calc_distance, calc_azimuth, calc_eve_coords  # (1)!


class Example:
    def __init__(self, stat_coords, eve_coords, distance, azimuth):  # (2)!
        self._stat_coords = stat_coords
        self._eve_coords = eve_coords
        self._distance = distance
        self._azimuth = azimuth

    @property
    def stat_coords(self):
        return self._stat_coords

    @stat_coords.setter
    def stat_coords(self, value):  # (3)!
        self._stat_coordes = value
        self._distance = calc_distance(self._stat_coords, self._eve_coords)
        self._azimuth = calc_azimuth(self._stat_coords, self._eve_coords)

    @property
    def eve_coords(self):
        return self._eve_coords

    @eve_coords.setter
    def eve_coords(self, value):  # (4)!
        self._eve_coords = value
        self._distance = calc_distance(self._stat_coords, self._eve_coords)
        self._azimuth = calc_azimuth(self._stat_coords, self._eve_coords)

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, value):  # (5)!
        self._distance = value
        self._eve_coords = calc_eve_coords(
            self._stat_coords, self._distance, self._azimuth
        )

    @property
    def azimuth(self):
        return self._azimuth

    @azimuth.setter
    def azimuth(self, value):  # (6)!
        self._azimuth = value
        self._eve_coords = calc_eve_coords(
            self._stat_coords, self._distance, self._azimuth
        )
