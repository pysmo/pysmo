import pandas as pd
import pytest

from pysmo import MiniOrientation, Orientation
from pysmo.classes import SAC, StationXML
from pysmo.exceptions import MissingValueError


def test_is_type_and_value_error() -> None:
    assert issubclass(MissingValueError, TypeError)
    assert issubclass(MissingValueError, ValueError)


@pytest.mark.parametrize("builtin", [TypeError, ValueError])
def test_caught_by_builtin(builtin: type[Exception]) -> None:
    with pytest.raises(builtin):
        SAC().station.latitude


def _orientation_or_none(orientation: Orientation) -> tuple[float, float] | None:
    try:
        return orientation.azimuth, orientation.dip
    except MissingValueError:
        return None


def test_missing_orientation_through_protocol() -> None:
    """Every Orientation implementation signals a missing value the same way."""
    stationxml = StationXML(
        network="IU",
        name="ANMO",
        location="00",
        channel="BHZ",
        latitude=34.9,
        longitude=-106.5,
        start_date=pd.Timestamp("2000-01-01T00:00:00Z"),
    )
    implementations: list[Orientation] = [SAC().orientation, stationxml]
    assert all(_orientation_or_none(o) is None for o in implementations)
    assert _orientation_or_none(MiniOrientation(azimuth=0, dip=-90)) == (0, -90)
