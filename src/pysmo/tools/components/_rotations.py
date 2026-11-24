"""Rotations to named coordinate systems."""

from pysmo import MiniSeismogram

from ._components import Components
from ._orientations import (
    lqt_orientations,
    rt_orientations,
    zne_orientations,
    zrt_orientations,
)

__all__ = ["rotate_to_lqt", "rotate_to_rt", "rotate_to_zne", "rotate_to_zrt"]


def rotate_to_zne(
    components: Components,
) -> tuple[MiniSeismogram, MiniSeismogram, MiniSeismogram]:
    """Rotate components to vertical, north, and east.

    The orientations are those from
    [`zne_orientations`][pysmo.tools.components.zne_orientations].

    Args:
        components: Three components.

    Returns:
        New Z, N, and E seismograms.

    Raises:
        ValueError: If `components` has only two components.
    """
    z, n, e = (components.project(o) for o in zne_orientations())
    return z, n, e


def rotate_to_rt(
    components: Components, backazimuth: float
) -> tuple[MiniSeismogram, MiniSeismogram]:
    """Rotate components to radial and transverse.

    The orientations are those from
    [`rt_orientations`][pysmo.tools.components.rt_orientations]. With three
    components, the vertical component is not part of the result.

    Args:
        components: Two or three components spanning the horizontal plane.
        backazimuth: Back azimuth (from the station to the source) in degrees.

    Returns:
        New R and T seismograms.

    Raises:
        ValueError: If `components` has two components that do not span the
            horizontal plane.
    """
    r, t = (components.project(o) for o in rt_orientations(backazimuth))
    return r, t


def rotate_to_zrt(
    components: Components, backazimuth: float
) -> tuple[MiniSeismogram, MiniSeismogram, MiniSeismogram]:
    """Rotate components to vertical, radial, and transverse.

    The orientations are those from
    [`zrt_orientations`][pysmo.tools.components.zrt_orientations].

    Args:
        components: Three components.
        backazimuth: Back azimuth (from the station to the source) in degrees.

    Returns:
        New Z, R, and T seismograms.

    Raises:
        ValueError: If `components` has only two components.
    """
    z, r, t = (components.project(o) for o in zrt_orientations(backazimuth))
    return z, r, t


def rotate_to_lqt(
    components: Components, backazimuth: float, incidence: float
) -> tuple[MiniSeismogram, MiniSeismogram, MiniSeismogram]:
    """Rotate components to the ray-oriented L, Q, and T system.

    The orientations are those from
    [`lqt_orientations`][pysmo.tools.components.lqt_orientations].

    Args:
        components: Three components.
        backazimuth: Back azimuth (from the station to the source) in degrees.
        incidence: Incidence angle from the vertical in degrees, from 0 to 90.

    Returns:
        New L, Q, and T seismograms.

    Raises:
        ValueError: If `incidence` is not between 0 and 90, or `components`
            has only two components.
    """
    orientations = lqt_orientations(backazimuth, incidence)
    l_, q, t = (components.project(o) for o in orientations)
    return l_, q, t
