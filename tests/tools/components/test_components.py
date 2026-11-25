import math
from pathlib import Path

import attrs
import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pysmo import MiniOrientation, MiniSeismogram, Orientation, Seismogram
from pysmo.classes import SAC
from pysmo.exceptions import MissingValueError
from pysmo.tools.components import (
    Components,
    lqt_orientations,
    rotate_to_lqt,
    rotate_to_rt,
    rotate_to_zne,
    rotate_to_zrt,
)

BEGIN_TIME = pd.Timestamp("2020-01-01", tz="UTC")
DELTA = pd.Timedelta(seconds=0.1)
NPTS = 50

backazimuths = st.floats(min_value=-720, max_value=720, allow_nan=False)
incidences = st.floats(min_value=0, max_value=90)
azimuths = st.floats(min_value=0, max_value=360, exclude_max=True)
dips = st.floats(min_value=-90, max_value=90)

Z = MiniOrientation(azimuth=0, dip=-90)
N = MiniOrientation(azimuth=0, dip=0)
E = MiniOrientation(azimuth=90, dip=0)


def _seismogram(
    data: npt.ArrayLike, begin_time: pd.Timestamp = BEGIN_TIME
) -> MiniSeismogram:
    return MiniSeismogram(
        begin_time=begin_time, delta=DELTA, data=np.array(data, dtype=float)
    )


def _random_zne(seed: int = 0) -> tuple[MiniSeismogram, ...]:
    rng = np.random.default_rng(seed)
    return tuple(_seismogram(rng.standard_normal(NPTS)) for _ in range(3))


def _vector(orientation: Orientation) -> np.ndarray:
    azimuth, dip = np.radians(orientation.azimuth), np.radians(orientation.dip)
    return np.array(
        [np.cos(dip) * np.cos(azimuth), np.cos(dip) * np.sin(azimuth), np.sin(dip)]
    )


class TestConstruction:
    def test_from_zne(self) -> None:
        z, n, e = _random_zne()
        components = Components.from_zne(z, n, e)
        assert components.orientations == (Z, N, E)
        assert components.begin_time == BEGIN_TIME
        assert components.delta == DELTA
        for out, original in zip(components.seismograms, (z, n, e)):
            np.testing.assert_array_equal(out.data, original.data)

    def test_from_ne(self) -> None:
        _, n, e = _random_zne()
        assert Components.from_ne(n, e).orientations == (N, E)

    def test_orientations_converted_to_mini(self, sacfile: Path) -> None:
        sac = SAC.from_file(sacfile)
        other = MiniSeismogram(
            begin_time=sac.seismogram.begin_time,
            delta=sac.seismogram.delta,
            data=sac.seismogram.data.copy(),
        )
        components = Components([(sac.seismogram, sac.orientation), (other, N)])
        assert components.orientations[0] == Z
        assert all(type(o) is MiniOrientation for o in components.orientations)

    def test_missing_orientation_raises(self) -> None:
        _, n, e = _random_zne()
        with pytest.raises(MissingValueError):
            Components([(n, SAC().orientation), (e, E)])

    @pytest.mark.parametrize("count", [0, 1, 4])
    def test_wrong_number_of_components(self, count: int) -> None:
        seismograms = _random_zne() * 2
        orientations = [Z, N, E, MiniOrientation(azimuth=45, dip=0)]
        pairs = list(zip(seismograms, orientations))[:count]
        with pytest.raises(ValueError, match="two or three"):
            Components(pairs)

    @pytest.mark.parametrize(
        "orientations",
        [
            (N, MiniOrientation(azimuth=180, dip=0)),
            (Z, N, MiniOrientation(azimuth=180, dip=0)),
            (N, E, MiniOrientation(azimuth=45, dip=0)),
        ],
    )
    def test_dependent_orientations(self, orientations: tuple[Orientation]) -> None:
        pairs = list(zip(_random_zne(), orientations))
        with pytest.raises(ValueError, match="linearly independent"):
            Components(pairs)

    def test_delta_mismatch(self) -> None:
        z, n, e = _random_zne()
        e.delta = DELTA * 2
        with pytest.raises(ValueError, match="delta"):
            Components.from_zne(z, n, e)

    def test_length_mismatch(self) -> None:
        z, n, e = _random_zne()
        e.data = e.data[:-1]
        with pytest.raises(ValueError, match="samples"):
            Components.from_zne(z, n, e)

    def test_begin_time_within_tolerance(self) -> None:
        z, n, e = _random_zne()
        e.begin_time = BEGIN_TIME + DELTA * 0.01
        assert Components.from_zne(z, n, e).begin_time == BEGIN_TIME

    def test_begin_time_mismatch(self) -> None:
        z, n, e = _random_zne()
        e.begin_time = BEGIN_TIME + DELTA * 0.02
        with pytest.raises(ValueError, match="begins at"):
            Components.from_zne(z, n, e)

    def test_data_are_copied(self, sacfile: Path) -> None:
        sac = SAC.from_file(sacfile)
        npts = len(sac.seismogram.data)
        other = _seismogram(np.ones(npts), begin_time=sac.seismogram.begin_time)
        other.delta = sac.seismogram.delta
        components = Components([(sac.seismogram, sac.orientation), (other, N)])
        original = sac.seismogram.data.copy()
        sac.seismogram.data[:] = 0
        other.data[:] = 0
        np.testing.assert_array_equal(components.seismograms[0].data, original)
        np.testing.assert_array_equal(components.seismograms[1].data, np.ones(npts))

    def test_seismograms_are_new_and_writable(self) -> None:
        z, n, e = _random_zne()
        components = Components.from_zne(z, n, e)
        out = components.seismograms
        assert all(type(s) is MiniSeismogram for s in out)
        assert out[0] is not z
        out[0].data[:] = 0
        assert np.any(components.seismograms[0].data != 0)

    def test_frozen(self) -> None:
        components = Components.from_zne(*_random_zne())
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            components.delta = DELTA * 2  # type: ignore[misc]

    def test_equality(self) -> None:
        assert Components.from_zne(*_random_zne()) == Components.from_zne(
            *_random_zne()
        )
        assert Components.from_zne(*_random_zne(0)) != Components.from_zne(
            *_random_zne(1)
        )


class TestProject:
    @given(azimuths, dips)
    def test_three_components_project_anywhere(
        self, azimuth: float, dip: float
    ) -> None:
        z, n, e = _random_zne()
        target = MiniOrientation(azimuth=azimuth, dip=dip)
        out = Components.from_zne(z, n, e).project(target)
        # Z is positive up, so the down component is -Z.
        motion = np.array([n.data, e.data, -z.data])
        np.testing.assert_allclose(out.data, _vector(target) @ motion, atol=1e-12)
        assert out.begin_time == BEGIN_TIME
        assert out.delta == DELTA

    def test_misoriented_horizontals_recover_north_and_east(self) -> None:
        """Measured orientations other than N/E still give the true N and E."""
        _, n, e = _random_zne()
        h1 = MiniOrientation(azimuth=20, dip=0)
        h2 = MiniOrientation(azimuth=130, dip=0)  # not perpendicular to h1
        record = [_seismogram(_vector(o)[:2] @ [n.data, e.data]) for o in (h1, h2)]
        components = Components([(record[0], h1), (record[1], h2)])
        np.testing.assert_allclose(components.project(N).data, n.data, atol=1e-12)
        np.testing.assert_allclose(components.project(E).data, e.data, atol=1e-12)

    def test_vertical_outside_horizontal_plane(self) -> None:
        _, n, e = _random_zne()
        with pytest.raises(ValueError, match="outside the plane"):
            Components.from_ne(n, e).project(Z)

    def test_vertical_plane(self) -> None:
        """Z and N span a vertical plane: E lies outside it."""
        z, n, _ = _random_zne()
        components = Components([(z, Z), (n, N)])
        np.testing.assert_allclose(components.project(Z).data, z.data, atol=1e-12)
        with pytest.raises(ValueError, match="outside the plane"):
            components.project(E)

    def test_span_tolerance(self) -> None:
        components = Components.from_ne(*_random_zne()[1:])
        components.project(MiniOrientation(azimuth=0, dip=0.5))
        with pytest.raises(ValueError, match="outside the plane"):
            components.project(MiniOrientation(azimuth=0, dip=2))


class TestRotate:
    @given(azimuths, st.floats(min_value=-80, max_value=80))
    def test_rotate_and_back(self, azimuth: float, dip: float) -> None:
        components = Components.from_zne(*_random_zne())
        targets = (
            MiniOrientation(azimuth=azimuth, dip=dip),
            MiniOrientation(azimuth=azimuth + 90, dip=0),
            MiniOrientation(azimuth=azimuth, dip=dip + 90 if dip < 0 else dip - 90),
        )
        rotated = components.rotate(targets)
        assert rotated.orientations == targets
        back = rotated.rotate(components.orientations)
        for out, original in zip(back.seismograms, components.seismograms):
            np.testing.assert_allclose(out.data, original.data, atol=1e-9)

    def test_rotate_needs_two_or_three(self) -> None:
        components = Components.from_zne(*_random_zne())
        with pytest.raises(ValueError, match="two or three"):
            components.rotate([N])

    def test_rotate_outside_plane(self) -> None:
        components = Components.from_ne(*_random_zne()[1:])
        with pytest.raises(ValueError, match="outside the plane"):
            components.rotate([Z, N])


class TestNamedRotations:
    @given(backazimuths)
    def test_rt_formulas(self, backazimuth: float) -> None:
        z, n, e = _random_zne()
        baz = math.radians(backazimuth)
        expected_r = -n.data * math.cos(baz) - e.data * math.sin(baz)
        expected_t = n.data * math.sin(baz) - e.data * math.cos(baz)
        for components in (Components.from_ne(n, e), Components.from_zne(z, n, e)):
            r, t = rotate_to_rt(components, backazimuth)
            np.testing.assert_allclose(r.data, expected_r, atol=1e-12)
            np.testing.assert_allclose(t.data, expected_t, atol=1e-12)

    @given(backazimuths)
    def test_zrt(self, backazimuth: float) -> None:
        z, n, e = _random_zne()
        components = Components.from_zne(z, n, e)
        z_out, r, t = rotate_to_zrt(components, backazimuth)
        np.testing.assert_allclose(z_out.data, z.data, atol=1e-12)
        r_expected, t_expected = rotate_to_rt(components, backazimuth)
        np.testing.assert_allclose(r.data, r_expected.data, atol=1e-12)
        np.testing.assert_allclose(t.data, t_expected.data, atol=1e-12)

    @given(backazimuths, incidences)
    def test_lqt_formulas(self, backazimuth: float, incidence: float) -> None:
        components = Components.from_zne(*_random_zne())
        z, r, t = rotate_to_zrt(components, backazimuth)
        inc = math.radians(incidence)
        l_, q, t_out = rotate_to_lqt(components, backazimuth, incidence)
        expected_l = z.data * math.cos(inc) + r.data * math.sin(inc)
        expected_q = -z.data * math.sin(inc) + r.data * math.cos(inc)
        np.testing.assert_allclose(l_.data, expected_l, atol=1e-12)
        np.testing.assert_allclose(q.data, expected_q, atol=1e-12)
        np.testing.assert_allclose(t_out.data, t.data, atol=1e-12)

    @given(backazimuths, incidences)
    def test_p_wave_lands_on_l(self, backazimuth: float, incidence: float) -> None:
        """Motion along the ray, away from the source, is all positive L."""
        signal = np.sin(np.linspace(0, 2 * np.pi, NPTS))
        direction = _vector(lqt_orientations(backazimuth, incidence)[0])
        north, east, down = np.outer(direction, signal)
        components = Components.from_zne(
            _seismogram(-down), _seismogram(north), _seismogram(east)
        )
        l_, q, t = rotate_to_lqt(components, backazimuth, incidence)
        np.testing.assert_allclose(l_.data, signal, atol=1e-12)
        np.testing.assert_allclose(q.data, 0, atol=1e-12)
        np.testing.assert_allclose(t.data, 0, atol=1e-12)

    def test_source_due_east(self) -> None:
        """A source due east: R points west, T points north."""
        _, n, e = _random_zne()
        r, t = rotate_to_rt(Components.from_ne(n, e), backazimuth=90)
        np.testing.assert_allclose(r.data, -e.data, atol=1e-12)
        np.testing.assert_allclose(t.data, n.data, atol=1e-12)

    def test_zne_round_trip(self) -> None:
        z, n, e = _random_zne()
        rotated = Components.from_zne(z, n, e).rotate(lqt_orientations(30, 20))
        for out, original in zip(rotate_to_zne(rotated), (z, n, e)):
            np.testing.assert_allclose(out.data, original.data, atol=1e-12)

    @pytest.mark.parametrize(
        "rotate",
        [
            rotate_to_zne,
            lambda c: rotate_to_zrt(c, 0),
            lambda c: rotate_to_lqt(c, 0, 10),
        ],
    )
    def test_three_component_rotations_need_three(self, rotate: object) -> None:
        components = Components.from_ne(*_random_zne()[1:])
        with pytest.raises(ValueError, match="outside the plane"):
            rotate(components)  # type: ignore[operator]

    def test_rt_from_vertical_plane_raises(self) -> None:
        z, n, _ = _random_zne()
        with pytest.raises(ValueError, match="outside the plane"):
            rotate_to_rt(Components([(z, Z), (n, N)]), backazimuth=0)


def test_accepts_any_seismogram(seismogram: Seismogram) -> None:
    other = MiniSeismogram(
        begin_time=seismogram.begin_time,
        delta=seismogram.delta,
        data=np.zeros(len(seismogram.data)),
    )
    components = Components([(seismogram, Z), (other, N)])
    np.testing.assert_array_equal(components.seismograms[0].data, seismogram.data)
