from pysmo import Location
from pysmo.functions import distance, azimuth, backazimuth
import pytest


def test_azimuth(stations: tuple[Location, ...], hypocenters: tuple[Location, ...]) -> None:
    """Calculate azimuth from Event and Station objects"""
    for location1 in hypocenters:
        for location2 in stations:
            azimuth_wgs84 = azimuth(location1, location2)
            azimuth_switched_wgs84 = azimuth(location2, location1)
            azimuth_clrk66 = azimuth(location1, location2, ellps='clrk66')
            assert pytest.approx(azimuth_wgs84) == 181.9199258637492
            assert pytest.approx(azimuth_switched_wgs84) == 2.4677533885335947
            assert pytest.approx(azimuth_clrk66) == 181.92001941872516


def test_backazimuth(stations: tuple[Location, ...], hypocenters: tuple[Location, ...]) -> None:
    """Calculate backazimuth from Event and Station objects"""
    for location1 in hypocenters:
        for location2 in stations:
            backazimuth_wgs84 = backazimuth(location1, location2)
            backazimuth_switched_wgs84 = backazimuth(location2, location1)
            backazimuth_clrk66 = backazimuth(location1, location2, ellps='clrk66')
            assert pytest.approx(backazimuth_wgs84) == 2.4677533885335947
            assert pytest.approx(backazimuth_switched_wgs84) == 181.9199258637492
            assert pytest.approx(backazimuth_clrk66) == 2.467847115319614


def test_distance(stations: tuple[Location, ...], hypocenters: tuple[Location, ...]) -> None:
    """Calculate distance from Event and Station objects"""
    for location1 in hypocenters:
        for location2 in stations:
            distance_wgs84 = distance(location1, location2)
            distance_clrk66 = distance(location1, location2, ellps='clrk66')
            assert pytest.approx(distance_wgs84) == 1889154.9940066523
            assert pytest.approx(distance_clrk66) == 1889121.7781364019
