from pyproj import Geod


def calc_gcd_from_floats(
    longitude_1: float, latitude_1: float, longitude_2: float, latitude_2: float
) -> float:
    g = Geod(ellps="WGS84")
    _, _, dist = g.inv(
        lons1=longitude_1, lats1=latitude_1, lons2=longitude_2, lats2=latitude_2
    )
    return round(dist / 1000)
