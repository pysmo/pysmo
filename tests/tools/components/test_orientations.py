import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pysmo import Orientation
from pysmo.tools.components import (
    lqt_orientations,
    rt_orientations,
    zne_orientations,
    zrt_orientations,
)

backazimuths = st.floats(min_value=-720, max_value=720, allow_nan=False)
incidences = st.floats(min_value=0, max_value=90)


def _vector(orientation: Orientation) -> np.ndarray:
    """Unit vector in a north–east–down frame."""
    azimuth, dip = np.radians(orientation.azimuth), np.radians(orientation.dip)
    return np.array(
        [np.cos(dip) * np.cos(azimuth), np.cos(dip) * np.sin(azimuth), np.sin(dip)]
    )


def test_zne_orientations() -> None:
    z, n, e = zne_orientations()
    assert (z.azimuth, z.dip) == (0, -90)
    assert (n.azimuth, n.dip) == (0, 0)
    assert (e.azimuth, e.dip) == (90, 0)


@given(backazimuths)
def test_rt_orientations(backazimuth: float) -> None:
    """R = -N cos(baz) - E sin(baz) and T = N sin(baz) - E cos(baz)."""
    r, t = rt_orientations(backazimuth)
    baz = math.radians(backazimuth)
    np.testing.assert_allclose(
        _vector(r), [-math.cos(baz), -math.sin(baz), 0], atol=1e-12
    )
    np.testing.assert_allclose(
        _vector(t), [math.sin(baz), -math.cos(baz), 0], atol=1e-12
    )


@given(backazimuths)
def test_zrt_orientations(backazimuth: float) -> None:
    z, r, t = zrt_orientations(backazimuth)
    assert (z.azimuth, z.dip) == (0, -90)
    assert (r, t) == rt_orientations(backazimuth)


@given(backazimuths, incidences)
def test_lqt_orientations_are_orthonormal_and_right_handed(
    backazimuth: float, incidence: float
) -> None:
    vectors = np.array([_vector(o) for o in lqt_orientations(backazimuth, incidence)])
    np.testing.assert_allclose(vectors @ vectors.T, np.eye(3), atol=1e-12)
    zrt = np.array([_vector(o) for o in zrt_orientations(backazimuth)])
    # Same handedness as Z/R/T.
    assert np.sign(np.linalg.det(vectors)) == np.sign(np.linalg.det(zrt))


@given(backazimuths)
def test_lqt_at_vertical_incidence_is_zrt(backazimuth: float) -> None:
    lqt = [_vector(o) for o in lqt_orientations(backazimuth, 0)]
    zrt = [_vector(o) for o in zrt_orientations(backazimuth)]
    np.testing.assert_allclose(lqt, zrt, atol=1e-12)


@given(backazimuths)
def test_lqt_at_grazing_incidence(backazimuth: float) -> None:
    """At 90° incidence the ray is horizontal: L is R, and Q points down."""
    l_, q, _ = lqt_orientations(backazimuth, 90)
    _, r, _ = zrt_orientations(backazimuth)
    np.testing.assert_allclose(_vector(l_), _vector(r), atol=1e-12)
    assert q.dip == 90


@pytest.mark.parametrize("incidence", [-0.1, 90.1, math.nan, math.inf])
def test_lqt_rejects_incidence_out_of_range(incidence: float) -> None:
    with pytest.raises(ValueError, match="incidence"):
        lqt_orientations(0, incidence)
