from pyproj import Geod  # We will use the Geod class for the calculations
from tutorial_seismogram import TutorialSeismogram


def calc_gcd_from_seismogram(seismogram: TutorialSeismogram) -> float:
    g = Geod(ellps="WGS84")
    # The g.inv method returns azimuth, back-azimuth and distance (in metres)
    # We only need the distance here:
    _, _, dist = g.inv(
        lons1=seismogram.event_longitude,
        lats1=seismogram.event_latitude,
        lons2=seismogram.station_longitude,
        lats2=seismogram.station_latitude,
    )
    return round(dist / 1000)
