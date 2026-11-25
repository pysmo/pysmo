"""The `Components` class."""

from collections.abc import Sequence
from typing import Self

import numpy as np
import numpy.typing as npt
import pandas as pd
from attrs import cmp_using, define, field

from pysmo import MiniOrientation, MiniSeismogram, Orientation, Seismogram

from ._orientations import zne_orientations

__all__ = ["Components"]

_SPAN_TOLERANCE = 0.02
"""Largest distance (about 1°) of a unit target vector from the components' span."""


def _unit_vector(orientation: Orientation) -> npt.NDArray[np.float64]:
    """Return the unit vector of an orientation in a north–east–down frame."""
    azimuth = np.radians(orientation.azimuth)
    dip = np.radians(orientation.dip)
    return np.array(
        [np.cos(dip) * np.cos(azimuth), np.cos(dip) * np.sin(azimuth), np.sin(dip)]
    )


def _check_orientations(orientations: Sequence[Orientation]) -> None:
    """Check there are two or three linearly independent orientations."""
    if len(orientations) not in (2, 3):
        raise ValueError(f"Expected two or three components, got {len(orientations)}.")
    vectors = np.array([_unit_vector(o) for o in orientations])
    if np.linalg.matrix_rank(vectors) < len(orientations):
        raise ValueError("Component orientations are not linearly independent.")


@define(frozen=True)
class Components:
    """Ground motion recorded by two or three components along known directions.

    A `Components` object is built from (seismogram, orientation) pairs, one
    per component. The orientations must be linearly independent, so two
    components span a plane (not necessarily horizontal) and three span all
    directions. The seismograms must share `delta` and length exactly, and
    their begin times must agree to within 1% of `delta`. They are not
    cropped to a common window. Cropping and resampling are done
    beforehand, with [`crop`][pysmo.functions.crop] and
    [`resample`][pysmo.functions.resample].

    The data are copied at construction, so changing the input seismograms
    afterwards has no effect. Every seismogram that comes out is a new
    [`MiniSeismogram`][pysmo.MiniSeismogram], including those from
    [`seismograms`][pysmo.tools.components.Components.seismograms].
    Attributes beyond the [`Seismogram`][pysmo.Seismogram] protocol are not
    kept.

    Examples:
        A north component recording motion towards the south, rotated for a
        source due north of the station:

        ```python
        >>> import numpy as np
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.components import Components, rotate_to_rt
        >>>
        >>> begin_time = pd.Timestamp("2020-01-01", tz="UTC")
        >>> delta = pd.Timedelta(seconds=0.1)
        >>> n = MiniSeismogram(
        ...     begin_time=begin_time, delta=delta, data=np.array([0.0, -1.0, 0.0])
        ... )
        >>> e = MiniSeismogram(begin_time=begin_time, delta=delta, data=np.zeros(3))
        >>> r, t = rotate_to_rt(Components.from_ne(n, e), backazimuth=0)
        >>> np.allclose(r.data, [0.0, 1.0, 0.0])
        True
        >>> np.allclose(t.data, 0.0)
        True
        >>>
        ```
    """

    _components: Sequence[tuple[Seismogram, Orientation]] = field(
        alias="components", repr=False, eq=False
    )
    """The (seismogram, orientation) pairs, one per component."""

    begin_time: pd.Timestamp = field(init=False)
    """Begin time of the first component."""

    delta: pd.Timedelta = field(init=False)
    """Sampling interval shared by all components."""

    orientations: tuple[MiniOrientation, ...] = field(init=False)
    """Orientations of the components, in input order."""

    _data: npt.NDArray[np.float64] = field(
        init=False, repr=False, eq=cmp_using(eq=np.array_equal)
    )
    """Read-only `(k, npts)` array of the recorded data."""

    _motion: npt.NDArray[np.float64] = field(init=False, repr=False, eq=False)
    """Read-only `(3, npts)` ground motion in a north–east–down frame."""

    _projector: npt.NDArray[np.float64] = field(init=False, repr=False, eq=False)
    """Projector onto the directions the components span."""

    def __attrs_post_init__(self) -> None:
        seismograms = [seismogram for seismogram, _ in self._components]
        orientations = tuple(
            MiniOrientation(azimuth=o.azimuth, dip=o.dip) for _, o in self._components
        )
        _check_orientations(orientations)

        first = seismograms[0]
        npts = len(first.data)
        for i, seismogram in enumerate(seismograms[1:], start=1):
            if seismogram.delta != first.delta:
                raise ValueError(
                    f"Component {i} has delta {seismogram.delta}, "
                    + f"component 0 has {first.delta}."
                )
            if len(seismogram.data) != npts:
                raise ValueError(
                    f"Component {i} has {len(seismogram.data)} samples, "
                    + f"component 0 has {npts}."
                )
            if abs(seismogram.begin_time - first.begin_time) > first.delta * 0.01:
                raise ValueError(
                    f"Component {i} begins at {seismogram.begin_time}, "
                    + f"component 0 at {first.begin_time}."
                )

        # np.array, not np.asarray, so live views (e.g. SacSeismogram) are copied.
        data = np.array([s.data for s in seismograms], dtype=np.float64)
        data.flags.writeable = False
        vectors = np.array([_unit_vector(o) for o in orientations])
        inverse = np.linalg.pinv(vectors)
        motion = inverse @ data
        motion.flags.writeable = False

        object.__setattr__(self, "begin_time", first.begin_time)
        object.__setattr__(self, "delta", first.delta)
        object.__setattr__(self, "orientations", orientations)
        object.__setattr__(self, "_data", data)
        object.__setattr__(self, "_motion", motion)
        object.__setattr__(self, "_projector", inverse @ vectors)

    @classmethod
    def from_zne(cls, z: Seismogram, n: Seismogram, e: Seismogram) -> Self:
        """Create a `Components` object from vertical, north, and east seismograms.

        The nominal orientations from
        [`zne_orientations`][pysmo.tools.components.zne_orientations] are
        used. Measured orientations, or components other than Z, N, and E,
        are given to the constructor.

        Args:
            z: Vertical component (positive up).
            n: North component.
            e: East component.

        Returns:
            Components with the nominal Z, N, and E orientations.
        """
        oz, on, oe = zne_orientations()
        return cls([(z, oz), (n, on), (e, oe)])

    @classmethod
    def from_ne(cls, n: Seismogram, e: Seismogram) -> Self:
        """Create a `Components` object from north and east seismograms.

        The nominal orientations from
        [`zne_orientations`][pysmo.tools.components.zne_orientations] are
        used. Measured orientations, or components other than N and E, are
        given to the constructor.

        Args:
            n: North component.
            e: East component.

        Returns:
            Components with the nominal N and E orientations.
        """
        _, on, oe = zne_orientations()
        return cls([(n, on), (e, oe)])

    @property
    def seismograms(self) -> tuple[MiniSeismogram, ...]:
        """New seismograms holding the recorded data, in input order."""
        return tuple(
            MiniSeismogram(
                begin_time=self.begin_time, delta=self.delta, data=row.copy()
            )
            for row in self._data
        )

    def project(self, orientation: Orientation) -> MiniSeismogram:
        """Return the seismogram a component along `orientation` would have recorded.

        With two components, `orientation` must lie in the plane they span.
        If the target orientations passed here (or to
        [`rotate`][pysmo.tools.components.Components.rotate]) are not
        mutually perpendicular, each result is a projection onto its own
        direction, not a coordinate in a skewed basis.

        Args:
            orientation: Orientation of the component to compute.

        Returns:
            New seismogram for the component along `orientation`.

        Raises:
            ValueError: If `orientation` lies outside the plane spanned by
                two components.
        """
        target = _unit_vector(orientation)
        if np.linalg.norm(target - self._projector @ target) > _SPAN_TOLERANCE:
            raise ValueError(
                f"Orientation (azimuth {orientation.azimuth}, dip "
                + f"{orientation.dip}) lies outside the plane spanned by the "
                + "components."
            )
        return MiniSeismogram(
            begin_time=self.begin_time, delta=self.delta, data=target @ self._motion
        )

    def rotate(self, orientations: Sequence[Orientation]) -> "Components":
        """Return the same ground motion recorded along new orientations.

        The new orientations are checked like those given to the constructor,
        and each must lie in the plane spanned by two components. See
        [`project`][pysmo.tools.components.Components.project].

        Args:
            orientations: Two or three linearly independent orientations.

        Returns:
            New `Components` object with the given orientations.

        Raises:
            ValueError: If the orientations are not two or three linearly
                independent directions, or one lies outside the plane
                spanned by two components.
        """
        _check_orientations(orientations)
        return Components([(self.project(o), o) for o in orientations])
