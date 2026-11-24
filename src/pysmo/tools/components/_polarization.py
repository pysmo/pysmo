"""Principal axes of ground motion."""

import numpy as np
import numpy.typing as npt
from attrs import define

from pysmo import MiniOrientation

from ._components import Components

__all__ = ["Polarization", "polarization"]

_HORIZONTAL_TOLERANCE = 1e-10
"""Largest vertical part of a unit axis that still counts as horizontal."""


@define(frozen=True)
class Polarization:
    """Principal axes of ground motion over a time window.

    Returned by [`polarization`][pysmo.tools.components.polarization].
    """

    eigenvalues: tuple[float, ...]
    """Eigenvalues of the covariance matrix, in descending order.

    Three with three components, two with two.
    """

    axis: MiniOrientation
    """Principal axis: the eigenvector of the largest eigenvalue.

    The axis is a line, so it is reported in a fixed form: the end pointing
    up (dip from -90 to 0), or for a horizontal axis the end with azimuth
    in [0, 180). The apparent incidence angle from the vertical is
    `dip + 90`.
    """

    rectilinearity: float
    """Rectilinearity, from 0 to 1, where 1 is linear motion."""

    planarity: float | None
    """Planarity, from 0 to 1, where 1 is motion in a plane.

    `None` with two components.
    """


def _canonical_axis(vector: npt.NDArray[np.float64]) -> MiniOrientation:
    """Return a unit vector in a north–east–down frame as an orientation."""
    north, east, down = vector
    azimuth = float(np.degrees(np.arctan2(east, north)))
    if abs(down) <= _HORIZONTAL_TOLERANCE:
        azimuth %= 180
        # A tiny negative azimuth rounds to 180 above.
        return MiniOrientation(azimuth=0 if azimuth == 180 else azimuth, dip=0)
    if down > 0:
        azimuth, down = azimuth + 180, -down
    if np.hypot(north, east) <= _HORIZONTAL_TOLERANCE:
        azimuth = 0.0
    dip = float(np.degrees(np.arctan2(down, np.hypot(north, east))))
    return MiniOrientation(azimuth=azimuth, dip=dip)


def polarization(components: Components) -> Polarization:
    """Return the principal axes of the ground motion in `components`.

    The covariance matrix of the ground motion is computed after removing
    each component's mean, and its eigenvalues `λ1 ≥ λ2 ≥ λ3` give the
    rectilinearity and planarity. With three components:

    - rectilinearity `1 - (λ2 + λ3) / (2 λ1)`
    - planarity `1 - 2 λ3 / (λ1 + λ2)`

    With two components the analysis stays in the plane they span, which
    need not be horizontal (e.g. Z and R for Rayleigh waves). There are two
    eigenvalues, the rectilinearity is `1 - λ2 / λ1`, and the planarity is
    `None`. This rectilinearity is not directly comparable with the
    three-component value.

    The result depends only on the ground motion, not on the directions
    the components were recorded along. The time window is set by cropping
    the seismograms before building `components`. The sense of elliptical
    motion (prograde or retrograde) is not determined.

    Args:
        components: Components to analyse.

    Returns:
        Eigenvalues, principal axis, rectilinearity, and planarity.

    Raises:
        ValueError: If the ground motion is constant.

    Examples:
        Motion along a line to the north-east is horizontal and perfectly
        rectilinear:

        ```python
        >>> import numpy as np
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.components import Components, polarization
        >>>
        >>> begin_time = pd.Timestamp("2020-01-01", tz="UTC")
        >>> delta = pd.Timedelta(seconds=0.1)
        >>> signal = np.sin(np.linspace(0, 4 * np.pi, 100))
        >>> z, n, e = (
        ...     MiniSeismogram(begin_time=begin_time, delta=delta, data=data)
        ...     for data in (np.zeros(100), signal, signal)
        ... )
        >>> result = polarization(Components.from_zne(z, n, e))
        >>> round(result.axis.azimuth, 6), round(result.axis.dip, 6)
        (45.0, 0.0)
        >>> round(result.rectilinearity, 6)
        1.0
        >>>
        ```

    References:
        Jurkevics, A. “Polarization Analysis of Three-Component Array Data.”
        Bulletin of the Seismological Society of America, vol. 78, no. 5,
        Oct. 1988, pp. 1725–43.
    """
    motion = components._motion
    centred = motion - motion.mean(axis=1, keepdims=True)
    covariance = centred @ centred.T / centred.shape[1]
    values, vectors = np.linalg.eigh(covariance)
    order = np.argsort(values)[::-1]
    count = len(components.orientations)
    eigenvalues = tuple(float(max(v, 0.0)) for v in values[order][:count])

    first = eigenvalues[0]
    # Removing the mean of constant data leaves rounding residue, not zeros.
    noise = 100 * np.finfo(np.float64).eps * np.abs(motion).max()
    if first <= noise**2:
        raise ValueError("Ground motion is constant.")
    if count == 3:
        second, third = eigenvalues[1:]
        rectilinearity = 1 - (second + third) / (2 * first)
        planarity: float | None = 1 - 2 * third / (first + second)
    else:
        rectilinearity = 1 - eigenvalues[1] / first
        planarity = None

    return Polarization(
        eigenvalues=eigenvalues,
        axis=_canonical_axis(vectors[:, order[0]]),
        rectilinearity=rectilinearity,
        planarity=planarity,
    )
