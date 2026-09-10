import pandas as pd
import pytest
from attrs import define, field

from pysmo.lib.validators import (
    is_latitude,
    is_longitude,
    is_nonzero,
    is_positive_timedelta,
)


@define
class Point:
    lat: float = field(validator=is_latitude)
    lon: float = field(validator=is_longitude)


def test_latitude_bounds() -> None:
    Point(lat=-90, lon=0)
    Point(lat=90, lon=0)
    for bad in (-91, 91):
        with pytest.raises(ValueError):
            Point(lat=bad, lon=0)


def test_longitude_bounds() -> None:
    Point(lat=0, lon=180)
    Point(lat=0, lon=-179.999)
    for bad in (-180.5, 181):
        with pytest.raises(ValueError):
            Point(lat=0, lon=bad)


@define
class Scale:
    factor: float = field(validator=is_nonzero)


def test_nonzero() -> None:
    Scale(factor=-1.5)
    Scale(factor=2)
    with pytest.raises(ValueError, match="must not be zero"):
        Scale(factor=0)


@define
class Sampling:
    delta: pd.Timedelta = field(validator=is_positive_timedelta)


def test_positive_timedelta() -> None:
    Sampling(delta=pd.Timedelta(seconds=0.1))
    with pytest.raises(ValueError):
        Sampling(delta=pd.Timedelta(0))
    with pytest.raises(TypeError):
        Sampling(delta=0.1)  # type: ignore[arg-type]
