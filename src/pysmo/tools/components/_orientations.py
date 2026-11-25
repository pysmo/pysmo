"""Named sets of target orientations for rotations."""

from pysmo import MiniOrientation

__all__ = [
    "lqt_orientations",
    "rt_orientations",
    "zne_orientations",
    "zrt_orientations",
]


def zne_orientations() -> tuple[MiniOrientation, MiniOrientation, MiniOrientation]:
    """Return the nominal vertical, north, and east orientations.

    Z points up (dip -90), N points north (azimuth 0, dip 0), and E points
    east (azimuth 90, dip 0).

    Returns:
        The Z, N, and E orientations.
    """
    return (
        MiniOrientation(azimuth=0, dip=-90),
        MiniOrientation(azimuth=0, dip=0),
        MiniOrientation(azimuth=90, dip=0),
    )


def rt_orientations(backazimuth: float) -> tuple[MiniOrientation, MiniOrientation]:
    """Return the radial and transverse orientations for a back azimuth.

    R is horizontal and points away from the source, at azimuth
    `backazimuth + 180`. T is horizontal and 90° clockwise from R, at azimuth
    `backazimuth + 270`. Both azimuths are wrapped into [0, 360).

    Args:
        backazimuth: Back azimuth (from the station to the source) in degrees.

    Returns:
        The R and T orientations.
    """
    return (
        MiniOrientation(azimuth=backazimuth + 180, dip=0),
        MiniOrientation(azimuth=backazimuth + 270, dip=0),
    )


def zrt_orientations(
    backazimuth: float,
) -> tuple[MiniOrientation, MiniOrientation, MiniOrientation]:
    """Return the vertical, radial, and transverse orientations for a back azimuth.

    Z points up (dip -90). R and T are as in
    [`rt_orientations`][pysmo.tools.components.rt_orientations].

    Args:
        backazimuth: Back azimuth (from the station to the source) in degrees.

    Returns:
        The Z, R, and T orientations.
    """
    radial, transverse = rt_orientations(backazimuth)
    return MiniOrientation(azimuth=0, dip=-90), radial, transverse


def lqt_orientations(
    backazimuth: float, incidence: float
) -> tuple[MiniOrientation, MiniOrientation, MiniOrientation]:
    """Return the L, Q, and T orientations for a back azimuth and incidence angle.

    L and Q lie in the vertical plane through the ray, at azimuth
    `backazimuth + 180`. L points along the direction of propagation
    (upwards, away from the source), at dip `incidence - 90`. Q is
    perpendicular to L in that plane, at dip `incidence`, so that L is Z
    and Q is R at vertical incidence. T is as in
    [`rt_orientations`][pysmo.tools.components.rt_orientations]. In terms
    of Z (positive up) and R:

    - `L = Z cos(incidence) + R sin(incidence)`
    - `Q = -Z sin(incidence) + R cos(incidence)`

    The incidence angle is measured from the vertical. Whether it is the
    apparent or the free-surface-corrected angle is up to the caller.

    Args:
        backazimuth: Back azimuth (from the station to the source) in degrees.
        incidence: Incidence angle from the vertical in degrees, from 0 to 90.

    Returns:
        The L, Q, and T orientations.

    Raises:
        ValueError: If `incidence` is not between 0 and 90.
    """
    if not 0 <= incidence <= 90:
        raise ValueError(f"incidence must be between 0 and 90, got {incidence}.")
    _, transverse = rt_orientations(backazimuth)
    return (
        MiniOrientation(azimuth=backazimuth + 180, dip=incidence - 90),
        MiniOrientation(azimuth=backazimuth + 180, dip=incidence),
        transverse,
    )
