import pytest

from pysmo import Location, MiniStation


def test_haversine(
    stations: tuple[Location, ...], hypocenters: tuple[Location, ...]
) -> None:
    """Calculate haversine distance from Event and Station objects"""
    from pysmo.tools.azdist import haversine

    for location1 in hypocenters:
        for location2 in stations:
            assert pytest.approx(haversine(location1, location2)) == 17.013879929551457
            assert pytest.approx(haversine(location2, location1)) == 17.013879929551457


def test_haversine_clamps_rounding_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rounding error pushing the clamped fraction above 1.0 must not raise."""
    from pysmo.tools import azdist

    location1 = MiniStation(
        name="AAA",
        network="AA",
        location="00",
        channel="AAA",
        latitude=0.0,
        longitude=0.0,
    )
    location2 = MiniStation(
        name="BBB",
        network="BB",
        location="00",
        channel="BBB",
        latitude=0.0,
        longitude=180.0,
    )
    # Force sin/cos to 1.0 so `a` evaluates to 2.0, mimicking the
    # floating-point overflow that can occur for near-antipodal points.
    monkeypatch.setattr(azdist.math, "sin", lambda x: 1.0)
    monkeypatch.setattr(azdist.math, "cos", lambda x: 1.0)

    assert azdist.haversine(location1, location2) == pytest.approx(180.0)


def test_azdist(
    stations: tuple[Location, ...], hypocenters: tuple[Location, ...]
) -> None:
    """Calculate azimuth from Event and Station objects"""
    from pysmo.tools.azdist import azimuth, backazimuth, distance

    for location1 in hypocenters:
        for location2 in stations:
            azimuth_wgs84 = azimuth(location1, location2)
            azimuth_switched_wgs84 = azimuth(location2, location1)
            azimuth_clrk66 = azimuth(location1, location2, ellps="clrk66")
            assert pytest.approx(azimuth_wgs84) == 181.9199258637492
            assert pytest.approx(azimuth_switched_wgs84) == 2.4677533885335947
            assert pytest.approx(azimuth_clrk66) == 181.92001941872516

            backazimuth_wgs84 = backazimuth(location1, location2)
            backazimuth_switched_wgs84 = backazimuth(location2, location1)
            backazimuth_clrk66 = backazimuth(location1, location2, ellps="clrk66")
            assert pytest.approx(backazimuth_wgs84) == 2.4677533885335947
            assert pytest.approx(backazimuth_switched_wgs84) == 181.9199258637492
            assert pytest.approx(backazimuth_clrk66) == 2.467847115319614

            distance_wgs84 = distance(location1, location2)
            distance_clrk66 = distance(location1, location2, ellps="clrk66")
            assert pytest.approx(distance_wgs84) == 1889154.9940066523
            assert pytest.approx(distance_clrk66) == 1889121.7781364019
