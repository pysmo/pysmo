import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from pysmo import Location, MiniLocation, MiniStation


def test_haversine(
    stations: tuple[Location, ...], hypocenters: tuple[Location, ...]
) -> None:
    """Calculate haversine distance from Event and Station objects"""
    from pysmo.tools.azdist import haversine

    for location1 in hypocenters:
        for location2 in stations:
            assert pytest.approx(haversine(location1, location2)) == 77.63835363183946
            assert pytest.approx(haversine(location2, location1)) == 77.63835363183946


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
            assert pytest.approx(azimuth_wgs84) == 332.23754008191094
            assert pytest.approx(azimuth_switched_wgs84) == 152.67365966211173
            assert pytest.approx(azimuth_clrk66) == 332.2361473607266

            backazimuth_wgs84 = backazimuth(location1, location2)
            backazimuth_switched_wgs84 = backazimuth(location2, location1)
            backazimuth_clrk66 = backazimuth(location1, location2, ellps="clrk66")
            assert pytest.approx(backazimuth_wgs84) == 152.67365966211173
            assert pytest.approx(backazimuth_switched_wgs84) == 332.23754008191094
            assert pytest.approx(backazimuth_clrk66) == 152.67227111331437

            distance_wgs84 = distance(location1, location2)
            distance_clrk66 = distance(location1, location2, ellps="clrk66")
            assert pytest.approx(distance_wgs84) == 8603325.124418385
            assert pytest.approx(distance_clrk66) == 8602982.024078561


# --- Property-based tests -----------------------------------------------
#
# The tests above pin exact values for one specific, real geometry (so a
# regression that shifts every result by the same amount, or breaks only
# for this particular fixture, would still be caught precisely). The tests
# below instead check invariants that must hold for *any* valid pair of
# locations, so a bug that happens to cancel out for one fixture's specific
# coordinates is still likely to be caught.
#
# Locations near the poles or (near-)antipodal to each other are excluded:
# azimuth/backazimuth are genuinely degenerate/multi-valued there (a
# rounding-error case for near-antipodal points is covered explicitly by
# test_haversine_clamps_rounding_error above), not a case these invariants
# are meant to cover.

_latitudes = st.floats(
    min_value=-89.9, max_value=89.9, allow_nan=False, allow_infinity=False
)
_longitudes = st.floats(
    min_value=-179.9, max_value=179.9, allow_nan=False, allow_infinity=False
)
_locations = st.builds(MiniLocation, latitude=_latitudes, longitude=_longitudes)


@settings(deadline=None)
@given(location1=_locations, location2=_locations)
def test_haversine_symmetric(location1: MiniLocation, location2: MiniLocation) -> None:
    from pysmo.tools.azdist import haversine

    assert haversine(location1, location2) == pytest.approx(
        haversine(location2, location1)
    )


@settings(deadline=None)
@given(location1=_locations, location2=_locations)
def test_haversine_and_distance_bounds(
    location1: MiniLocation, location2: MiniLocation
) -> None:
    from pysmo.tools.azdist import distance, haversine

    assert 0 <= haversine(location1, location2) <= 180
    assert distance(location1, location2) >= 0


def _angles_equivalent(a: float, b: float, tol: float = 1e-6) -> bool:
    """True if bearings `a`/`b` (degrees) point the same direction.

    0 and 360 both mean "due north" but are not numerically equal, so a
    plain `pytest.approx` comparison spuriously fails right at that
    wraparound boundary.
    """
    diff = abs(a - b) % 360
    return min(diff, 360 - diff) < tol


@settings(deadline=None)
@given(location1=_locations, location2=_locations)
def test_azimuth_backazimuth_are_swapped_by_direction(
    location1: MiniLocation, location2: MiniLocation
) -> None:
    from pysmo.tools.azdist import azimuth, backazimuth, haversine

    # Exclude near-identical and near-antipodal pairs: azimuth/backazimuth
    # are degenerate (multi-valued) exactly at those extremes.
    assume(0.5 < haversine(location1, location2) < 179.5)

    assert _angles_equivalent(
        azimuth(location1, location2), backazimuth(location2, location1)
    )
    assert _angles_equivalent(
        backazimuth(location1, location2), azimuth(location2, location1)
    )
