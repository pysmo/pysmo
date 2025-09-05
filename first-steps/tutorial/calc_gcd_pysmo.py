from pyproj import Geod
from pysmo import Location


def calc_gcd(point1: Location, point2: Location) -> float:
    g = Geod(ellps="WGS84")
    _, _, dist = g.inv(
        lons1=point1.longitude,
        lats1=point1.latitude,
        lons2=point2.longitude,
        lats2=point2.latitude,
    )
    return round(dist / 1000)
