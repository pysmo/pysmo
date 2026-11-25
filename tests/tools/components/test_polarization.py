import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pysmo import MiniOrientation, MiniSeismogram, Orientation
from pysmo.tools.components import (
    Components,
    polarization,
    rotate_to_rt,
    rt_orientations,
    zne_orientations,
)

BEGIN_TIME = pd.Timestamp("2020-01-01", tz="UTC")
DELTA = pd.Timedelta(seconds=0.1)
NPTS = 200
SIGNAL = np.sin(np.linspace(0, 6 * np.pi, NPTS, endpoint=False))
QUADRATURE = np.cos(np.linspace(0, 6 * np.pi, NPTS, endpoint=False))

azimuths = st.floats(min_value=0, max_value=360, exclude_max=True)
dips = st.floats(min_value=-90, max_value=90)


def _vector(orientation: Orientation) -> npt.NDArray[np.float64]:
    azimuth, dip = np.radians(orientation.azimuth), np.radians(orientation.dip)
    return np.array(
        [np.cos(dip) * np.cos(azimuth), np.cos(dip) * np.sin(azimuth), np.sin(dip)]
    )


def _record(
    motion: npt.NDArray[np.float64], orientations: tuple[Orientation, ...]
) -> Components:
    """Record `(3, npts)` north–east–down motion along `orientations`."""
    return Components(
        [
            (
                MiniSeismogram(
                    begin_time=BEGIN_TIME, delta=DELTA, data=_vector(o) @ motion
                ),
                o,
            )
            for o in orientations
        ]
    )


def _linear(direction: Orientation) -> npt.NDArray[np.float64]:
    return np.outer(_vector(direction), SIGNAL)


def _same_line(a: Orientation, b: Orientation) -> bool:
    return bool(np.isclose(abs(_vector(a) @ _vector(b)), 1, atol=1e-9))


@given(azimuths, dips)
def test_linear_motion(azimuth: float, dip: float) -> None:
    direction = MiniOrientation(azimuth=azimuth, dip=dip)
    result = polarization(_record(_linear(direction), zne_orientations()))
    assert _same_line(result.axis, direction)
    assert result.rectilinearity == pytest.approx(1)
    assert result.planarity == pytest.approx(1)
    assert len(result.eigenvalues) == 3
    assert result.eigenvalues[1:] == pytest.approx((0, 0), abs=1e-12)


@given(azimuths, dips)
def test_axis_points_up(azimuth: float, dip: float) -> None:
    result = polarization(
        _record(_linear(MiniOrientation(azimuth=azimuth, dip=dip)), zne_orientations())
    )
    assert -90 <= result.axis.dip <= 0
    if result.axis.dip == 0:
        assert 0 <= result.axis.azimuth < 180


@pytest.mark.parametrize("dip", [90, -90])
def test_vertical_axis(dip: float) -> None:
    result = polarization(
        _record(_linear(MiniOrientation(azimuth=0, dip=dip)), zne_orientations())
    )
    assert (result.axis.azimuth, result.axis.dip) == (0, -90)


@pytest.mark.parametrize("azimuth", [0, 30, 90, 180, 210, 270, 330])
def test_horizontal_axis_azimuth(azimuth: float) -> None:
    result = polarization(
        _record(_linear(MiniOrientation(azimuth=azimuth, dip=0)), zne_orientations())
    )
    assert result.axis.dip == 0
    assert 0 <= result.axis.azimuth < 180
    difference = (result.axis.azimuth - azimuth + 90) % 180 - 90
    assert difference == pytest.approx(0, abs=1e-9)


def test_circular_motion_in_a_plane() -> None:
    n, e = (
        _vector(MiniOrientation(azimuth=0, dip=0)),
        _vector(MiniOrientation(azimuth=90, dip=0)),
    )
    motion = np.outer(n, SIGNAL) + np.outer(e, QUADRATURE)
    result = polarization(_record(motion, zne_orientations()))
    assert result.eigenvalues[0] == pytest.approx(result.eigenvalues[1])
    assert result.eigenvalues[2] == pytest.approx(0, abs=1e-12)
    assert result.rectilinearity == pytest.approx(0.5)
    assert result.planarity == pytest.approx(1)


def test_isotropic_motion() -> None:
    rng = np.random.default_rng(0)
    motion = rng.standard_normal((3, 100_000))
    result = polarization(_record(motion, zne_orientations()))
    assert result.rectilinearity == pytest.approx(0, abs=0.02)
    assert result.planarity == pytest.approx(0, abs=0.02)


def test_eigenvalues_descending() -> None:
    rng = np.random.default_rng(1)
    result = polarization(_record(rng.standard_normal((3, NPTS)), zne_orientations()))
    assert list(result.eigenvalues) == sorted(result.eigenvalues, reverse=True)


def test_mean_removed() -> None:
    direction = MiniOrientation(azimuth=60, dip=20)
    motion = _linear(direction)
    offset = motion + np.array([[5.0], [-3.0], [2.0]])
    expected = polarization(_record(motion, zne_orientations()))
    result = polarization(_record(offset, zne_orientations()))
    assert result.eigenvalues == pytest.approx(expected.eigenvalues)
    assert _same_line(result.axis, direction)


@given(azimuths)
def test_independent_of_recording_orientations(azimuth: float) -> None:
    rng = np.random.default_rng(2)
    motion = rng.standard_normal((3, NPTS))
    tilted = (
        MiniOrientation(azimuth=azimuth, dip=-60),
        MiniOrientation(azimuth=azimuth + 100, dip=10),
        MiniOrientation(azimuth=azimuth + 200, dip=30),
    )
    expected = polarization(_record(motion, zne_orientations()))
    result = polarization(_record(motion, tilted))
    assert result.eigenvalues == pytest.approx(expected.eigenvalues)
    assert result.rectilinearity == pytest.approx(expected.rectilinearity)
    assert result.planarity == pytest.approx(expected.planarity)
    assert _same_line(result.axis, expected.axis)


class TestTwoComponents:
    @given(azimuths)
    def test_horizontal_pair(self, azimuth: float) -> None:
        direction = MiniOrientation(azimuth=azimuth, dip=0)
        _, n, e = zne_orientations()
        result = polarization(_record(_linear(direction), (n, e)))
        assert len(result.eigenvalues) == 2
        assert result.planarity is None
        assert result.rectilinearity == pytest.approx(1)
        assert result.axis.dip == 0
        assert 0 <= result.axis.azimuth < 180
        assert _same_line(result.axis, direction)

    def test_vertical_plane(self) -> None:
        """Z and R: the axis is in the plane and points up."""
        z, _, _ = zne_orientations()
        r, _ = rt_orientations(30)
        direction = MiniOrientation(azimuth=r.azimuth + 180, dip=40)
        result = polarization(_record(_linear(direction), (z, r)))
        assert result.axis.dip == pytest.approx(-40)
        assert result.axis.azimuth == pytest.approx(r.azimuth)

    def test_motion_outside_plane_is_ignored(self) -> None:
        """Only the part of the motion in the plane is analysed."""
        z, n, e = zne_orientations()
        motion = np.outer(_vector(n), SIGNAL) + np.outer(_vector(z), QUADRATURE)
        result = polarization(_record(motion, (n, e)))
        assert result.rectilinearity == pytest.approx(1)
        assert _same_line(result.axis, n)

    def test_elliptical(self) -> None:
        _, n, e = zne_orientations()
        motion = np.outer(_vector(n), SIGNAL) + 0.5 * np.outer(_vector(e), QUADRATURE)
        result = polarization(_record(motion, (n, e)))
        assert result.rectilinearity == pytest.approx(0.75)

    def test_love_wave_on_transverse(self) -> None:
        """Motion along T from N/E rotates to all-transverse energy."""
        _, t = rt_orientations(70)
        components = _record(_linear(t), zne_orientations()[1:])
        result = polarization(components)
        assert _same_line(result.axis, t)
        r_seismogram, _ = rotate_to_rt(components, backazimuth=70)
        np.testing.assert_allclose(r_seismogram.data, 0, atol=1e-12)


@pytest.mark.parametrize("value", [0.0, 0.1, 1.0, 3.3, 1e5, 1e-9])
def test_constant_motion_raises(value: float) -> None:
    """Rounding residue from removing the mean is not motion."""
    motion = np.array([[value], [3 * value], [7 * value]]) * np.ones((3, NPTS))
    with pytest.raises(ValueError, match="constant"):
        polarization(_record(motion, zne_orientations()))


def test_small_motion_is_analysed() -> None:
    direction = MiniOrientation(azimuth=60, dip=20)
    result = polarization(_record(1e-12 * _linear(direction), zne_orientations()))
    assert result.rectilinearity == pytest.approx(1)
    assert _same_line(result.axis, direction)
