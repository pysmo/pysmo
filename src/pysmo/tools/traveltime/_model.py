"""Flattened-earth slowness profiles for the tau-p solver.

A Buland–Chapman (1983) tau-p solver needs, for each body-wave type, the
velocity model expressed as slowness `u = r / (a·v)` against the flattened
depth `z = a·ln(a/r)`, where `a` is the Earth's radius and `r` is the
geocentric radius. Each published model is a `.tvel` file in `data/`,
interpolated linearly in depth onto a `GRID_STEP_KM` grid, keeping both
sides of every velocity discontinuity so the solver can distinguish rays
that turn exactly at a boundary.

The grid resolution matches TauP's default internal sampling, keeping
travel times consistent with reference TauP calculations to within a few
milliseconds. Both profiles stop at the core–mantle boundary, whose depth
is read from the model as the point where `vs` first drops to zero: the
modelled phases (P, S, and the CMB reflections) never sample the core.
"""

import math
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

import numpy as np
import numpy.typing as npt

from pysmo.tools.traveltime._types import Model, Wave

_EARTH_RADIUS_KM = 6371.0
_GRID_STEP_KM = 1.0

# Slack for floating-point depth comparisons, in kilometres: grid
# resampling in `_profile` and the integration bounds in `integrate`.
# A micron; far below any physically meaningful depth difference.
_DEPTH_TOLERANCE_KM = 1e-9

_DATA_DIR = Path(__file__).resolve().parent / "data"


def _flattened_depth(depth_km: float) -> float:
    """Convert a geocentric depth in kilometres to flattened depth.

    Args:
        depth_km: Geocentric depth below the surface, in kilometres.

    Returns:
        The Buland–Chapman flattened depth `a·ln(a/r)`, in kilometres.
    """
    return _EARTH_RADIUS_KM * math.log(_EARTH_RADIUS_KM / (_EARTH_RADIUS_KM - depth_km))


@dataclass(frozen=True)
class _ModelRow:
    """One raw `depth_km, vp, vs, rho` row of the `.tvel` table."""

    depth_km: float
    """Depth below the surface, in kilometres."""

    vp: float
    """Compressional wave velocity, in kilometres per second."""

    vs: float
    """Shear wave velocity, in kilometres per second."""

    rho: float
    """Density, in grams per cubic centimetre."""

    def velocity(self, wave: Wave) -> float:
        """Return the P or S velocity of this row.

        Args:
            wave: The wave type whose velocity is wanted.

        Returns:
            The `vp` value for `"P"`, or the `vs` value for `"S"`.
        """
        return self.vp if wave == "P" else self.vs


@lru_cache
def _read_model_rows(model: Model) -> tuple[_ModelRow, ...]:
    """Parse a model's `.tvel` file into `_ModelRow` records."""
    path = _DATA_DIR / f"{model}.tvel"
    rows: list[_ModelRow] = []
    # A .tvel file opens with exactly two free-text comment lines; every
    # line after that is a `depth vp vs rho` row.
    for line_number, line in enumerate(path.read_text().splitlines()[2:], start=3):
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 4:
            raise ValueError(
                f"{path.name} line {line_number}: expected 'depth vp vs rho', "
                + f"got {line.strip()!r}."
            )
        rows.append(
            _ModelRow(
                depth_km=float(parts[0]),
                vp=float(parts[1]),
                vs=float(parts[2]),
                rho=float(parts[3]),
            )
        )
    if len(rows) < 2 or any(b.depth_km < a.depth_km for a, b in pairwise(rows)):
        raise ValueError(f"{path.name}: needs >=2 rows of non-decreasing depth.")
    return tuple(rows)


@lru_cache
def cmb_depth_km(model: Model) -> float:
    """Depth of a model's core–mantle boundary, in kilometres.

    Taken as the first depth at which the shear velocity drops to zero.

    Args:
        model: Velocity model name.

    Returns:
        The core–mantle boundary depth in kilometres.
    """
    for row in _read_model_rows(model):
        if row.vs <= 0.0:
            return row.depth_km
    raise ValueError(
        f"model {model!r} has no core–mantle boundary: vs never reaches zero"
    )


def _profile(model: Model, wave: Wave) -> list[tuple[float, float]]:
    """Build the fine flattened slowness profile for one wave type.

    Reads the model rows in `depth, vp, vs, rho` order and resamples the
    chosen wave's velocity linearly in depth onto the grid, preserving a
    flush pair of duplicate-depth samples at every discontinuity so that a
    `turn_depth` lookup can hit a velocity jump exactly. Rows at or below
    the core–mantle boundary are dropped.

    Args:
        model: Velocity model name.
        wave: The wave type to profile.

    Returns:
        Flat-earth samples as `(flattened depth in km, slowness in s/km)`
        pairs, ordered by increasing depth.
    """
    cmb_km = cmb_depth_km(model)
    samples: list[tuple[float, float]] = []
    for top, bottom in pairwise(_read_model_rows(model)):
        d1, d2 = top.depth_km, bottom.depth_km
        v1, v2 = top.velocity(wave), bottom.velocity(wave)

        # Nothing to sample: no velocity, or at or below the core–mantle
        # boundary.
        if v1 <= 0 or v2 <= 0 or d1 >= cmb_km - _DEPTH_TOLERANCE_KM:
            continue

        # Zero-thickness layer: a velocity discontinuity. Keep a sample on
        # each side so a turning-point lookup can land on the jump.
        if d2 <= d1:
            samples.append((d1, v1))
            samples.append((d1, v2))
            continue

        # Normal layer: its top sample, then the interior resampled onto
        # the fixed grid linear in depth, then the base sample unless it
        # sits past the boundary.
        if (not samples) or samples[-1][0] < d1 - _DEPTH_TOLERANCE_KM:
            samples.append((d1, v1))
        n_steps = int((d2 - d1 - _DEPTH_TOLERANCE_KM) / _GRID_STEP_KM)
        for step in range(1, n_steps + 1):
            depth = d1 + step * _GRID_STEP_KM
            velocity = v1 + ((depth - d1) / (d2 - d1)) * (v2 - v1)
            samples.append((depth, velocity))
        if d2 <= cmb_km + _DEPTH_TOLERANCE_KM:
            samples.append((d2, v2))

    # Every sampled velocity is positive and every depth is above the
    # core–mantle boundary, so the earth-flattening transform is all that
    # is left to apply.
    profile: list[tuple[float, float]] = []
    for depth, velocity in samples:
        radius = _EARTH_RADIUS_KM - depth
        profile.append(
            (_flattened_depth(depth), (radius / _EARTH_RADIUS_KM) / velocity)
        )
    return profile


def _layer_integrals(
    u1: float, u2: float, z1: float, z2: float, p: float
) -> tuple[float, float]:
    """Analytic `(tau, delta)` contribution of one linear slowness layer.

    The slowness is linear in depth within the layer, so the Buland &
    Chapman closed forms are exact. For a constant-slowness layer the
    integrand is evaluated directly. The logarithmic ratio form avoids the
    loss of precision from subtracting two nearly-equal endpoint integrals
    in near-turning layers.

    `_layer_integrals_vec` is the same computation across a whole profile
    at once and is the hot path; this scalar form is used only for the
    single partial layer straddling the integration end point.

    Args:
        u1: Slowness at the top of the layer, in seconds per kilometre.
        u2: Slowness at the bottom of the layer, in seconds per kilometre.
        z1: Flattened depth of the top of the layer, in kilometres.
        z2: Flattened depth of the base of the layer, in kilometres.
        p: Ray parameter, in seconds per kilometre.

    Returns:
        The `(tau, delta)` pair, in seconds and kilometres respectively
        (`delta` is the flattened horizontal distance, not an angle).
        Terms below the ray's turning point (`u < p`) are clamped to zero,
        matching `_layer_integrals_vec`; the caller masks such layers out.
    """
    pp = p * p
    f1 = math.sqrt(max(u1 * u1 - pp, 0.0))
    f2 = math.sqrt(max(u2 * u2 - pp, 0.0))
    slope = (u2 - u1) / (z2 - z1)
    if slope == 0:
        s = f1 if f1 != 0.0 else 1.0
        thickness = z2 - z1
        return (u1 * u1 / s) * thickness, (p / s) * thickness
    ratio = (u2 + f2) / (u1 + f1)
    tau = 0.5 * (u2 * f2 - u1 * f1 - pp * math.log(ratio)) / slope
    delta = p * math.log(ratio) / slope
    return tau, delta


def _layer_integrals_vec(
    u1: npt.NDArray[np.float64],
    u2: npt.NDArray[np.float64],
    z1: npt.NDArray[np.float64],
    z2: npt.NDArray[np.float64],
    p: float,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """`_layer_integrals` evaluated over an array of layers at once.

    The same closed forms as the scalar version, one `(tau, delta)` pair
    per layer. This is the hot path: `integrate` calls it once per ray
    parameter over every layer above the turning point, and only sums the
    layers it knows lie above it; the closed form itself is not valid for a
    layer below the turning point, so a caller must not sum one.

    Args:
        u1: Slowness at the top of each layer, in seconds per kilometre.
        u2: Slowness at the base of each layer, in seconds per kilometre.
        z1: Flattened depth of the top of each layer, in kilometres.
        z2: Flattened depth of the base of each layer, in kilometres.
        p: Ray parameter, in seconds per kilometre.

    Returns:
        The per-layer `(tau, delta)` arrays, in seconds and kilometres
        respectively (`delta` is the flattened horizontal distance, not an
        angle).
    """
    dz = z2 - z1
    du = u2 - u1
    pp = p * p
    linear = du != 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        f1 = np.sqrt(np.maximum(u1 * u1 - pp, 0.0))
        f2 = np.sqrt(np.maximum(u2 * u2 - pp, 0.0))
        log_ratio = np.log((u2 + f2) / (u1 + f1))
        slope = np.where(linear, du / dz, 1.0)
        s = np.where(f1 == 0.0, 1.0, f1)
        tau = np.where(
            linear,
            0.5 * (u2 * f2 - u1 * f1 - pp * log_ratio) / slope,
            u1 * u1 / s * dz,
        )
        delta = np.where(linear, p * log_ratio / slope, p / s * dz)
    return tau, delta


class SlownessProfile:
    """A flattened slowness profile for one wave type of a velocity model.

    Attributes:
        z: Flattened depth of each sample, in kilometres, non-decreasing.
        u: Slowness `r / (a·v)` at each sample, in seconds per kilometre.
        branch_knots: Slownesses on both sides of every velocity
            discontinuity, in seconds per kilometre. Epicentral distance is
            not monotonic in ray parameter across a discontinuity, so a
            turning-ray search split at these values keeps each sub-range
            monotonic and can pick the first arrival where the branches
            overlap (an upper-mantle triplication).
    """

    def __init__(self, model: Model, wave: Wave) -> None:
        """Build the profile for a model and wave type.

        Args:
            model: Velocity model name.
            wave: The wave type to profile.
        """
        data = np.array(_profile(model, wave), dtype=np.float64)
        self.z: npt.NDArray[np.float64] = data[:, 0]
        self.u: npt.NDArray[np.float64] = data[:, 1]
        # Adjacent-sample layers, kept so the vectorised integrals work on
        # arrays. `_real` masks out the zero-thickness pairs left at
        # velocity discontinuities.
        self._z1, self._z2 = self.z[:-1], self.z[1:]
        self._u1, self._u2 = self.u[:-1], self.u[1:]
        self._dz = self._z2 - self._z1
        self._real = self._dz > 0.0
        self.branch_knots: npt.NDArray[np.float64] = np.unique(
            np.concatenate([self._u1[~self._real], self._u2[~self._real]])
        )

    def u_at(self, z: float) -> float:
        """Interpolate slowness at a flattened depth (linear in depth).

        Args:
            z: Flattened depth, in kilometres.

        Returns:
            The slowness in seconds per kilometre at depth *z*.
        """
        band = self._real & (self._z1 <= z) & (z <= self._z2)
        if not band.any():
            return float(self.u[-1])
        i = int(np.argmax(band))
        fraction = (z - self._z1[i]) / self._dz[i]
        return float(self._u1[i] + fraction * (self._u2[i] - self._u1[i]))

    def turn_depth(self, p: float) -> float | None:
        """Flattened depth where a ray of ray parameter *p* turns, or `None`.

        A ray turns in the layer whose slowness drops through *p*, or
        exactly at a velocity discontinuity when the top of the jump
        exceeds *p* but its bottom does not.

        Args:
            p: Ray parameter, in seconds per kilometre.

        Returns:
            Flattened turning depth in kilometres, or `None` when no layer
            drops through *p* (e.g. *p* below the slowness at the base of
            the profile).
        """
        crossing = (self._u1 > p) & (self._u2 <= p)
        if not crossing.any():
            return None
        i = int(np.argmax(crossing))
        if self._dz[i] > 0.0:
            return float(
                self._z1[i]
                + (self._u1[i] - p) / (self._u1[i] - self._u2[i]) * self._dz[i]
            )
        return float(self._z1[i])

    def integrate(self, z_end: float, p: float) -> tuple[float, float]:
        """Accumulate `(tau, delta)` from the surface down to flattened depth *z_end*.

        The ray is assumed to descend from the surface, so layers between
        the surface and *z_end* contribute to both integrals.

        Args:
            z_end: Flattened depth of the integration end point, in
                kilometres.
            p: Ray parameter, in seconds per kilometre.

        Returns:
            The `(tau, delta)` pair, in seconds and kilometres respectively
            (`delta` is the flattened horizontal distance, not an angle).
        """
        # Only layers above z_end contribute, and z2 is sorted, so those
        # are a prefix; the layer straddling z_end is handled separately.
        n = int(np.searchsorted(self._z2, z_end + _DEPTH_TOLERANCE_KM, side="right"))
        real = self._real[:n]
        tau_layers, delta_layers = _layer_integrals_vec(
            self._u1[:n], self._u2[:n], self._z1[:n], self._z2[:n], p
        )
        tau = float(np.sum(tau_layers, where=real))
        delta = float(np.sum(delta_layers, where=real))
        reached = float(np.max(self._z2[:n], where=real, initial=0.0))
        if reached < z_end - _DEPTH_TOLERANCE_KM:
            straddle = (
                self._real
                & (self._z1 <= z_end - _DEPTH_TOLERANCE_KM)
                & (self._z2 >= z_end - _DEPTH_TOLERANCE_KM)
            )
            if straddle.any():
                i = int(np.argmax(straddle))
                z1_i, u1_i = float(self._z1[i]), float(self._u1[i])
                u_end = max(
                    u1_i + (z_end - z1_i) / self._dz[i] * (self._u2[i] - self._u1[i]),
                    p,
                )
                t, d = _layer_integrals(u1_i, u_end, z1_i, z_end, p)
                tau += t
                delta += d
        return tau, delta

    def direct_time(self, z_s: float, p: float) -> tuple[float, float] | None:
        """`(travel_time, flat_delta)` of a down-going ray turning below depth *z_s*.

        Returns `None` when the ray of parameter *p* has no turning point,
        or turns above the source.

        Args:
            z_s: Flattened source depth, in kilometres.
            p: Ray parameter, in seconds per kilometre.

        Returns:
            A `(travel_time, flat_delta)` pair, with flat_delta in
            kilometres (divide by the Earth radius for radians), or `None`
            when the ray does not turn below *z_s*.
        """
        z_t = self.turn_depth(p)
        if z_t is None or z_t < z_s:
            return None
        tau_s, delta_s = self.integrate(z_s, p)
        tau_t, delta_t = self.integrate(z_t, p)
        tau = 2 * tau_t - tau_s
        delta = 2 * delta_t - delta_s
        return tau + p * delta, delta


@lru_cache
def get_profile(model: Model, wave: Wave) -> SlownessProfile:
    """Return the slowness profile for a model and wave type, built on first use.

    Args:
        model: Velocity model name.
        wave: The wave type to return.

    Returns:
        The `SlownessProfile`.
    """
    return SlownessProfile(model, wave)
