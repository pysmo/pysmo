"""Travel-time computation for teleseismic body-wave phases.

Implements the Buland–Chapman tau-p relations by direct integration of a
`.tvel` velocity model, with no precomputed tables. Two ray families are
modelled:

* **Down-going turning rays** (P, S) bend round at a slowness turning
  point above the core–mantle boundary.
* **Core–mantle boundary reflections** (PcP, ScS, PcS, ScP) reflect at
  the CMB; the down- and up-going legs may share a wave type or convert
  between P and S at the reflector.

For each requested phase the ray parameter whose ray reaches the
requested epicentral distance is found by bisection over that phase's
branch, then the travel time follows from `t = τ + p·Δ`.

Short distances with no solution on the modelled branch have the phase
omitted from the result, as do distances beyond the CMB grazing limit
(the core shadow).
"""

import math
from collections.abc import Callable, Sequence
from itertools import pairwise
from typing import get_args

from pysmo.tools.traveltime._model import (
    _EARTH_RADIUS_KM,
    SlownessProfile,
    _flattened_depth,
    cmb_depth_km,
    get_profile,
)
from pysmo.tools.traveltime._types import Model, Phase, Wave

# Turning phase -> the single wave type its ray propagates as. The ray
# bends round at a slowness turning point above the core–mantle boundary.
_TURNING_PHASES: dict[str, Wave] = {"P": "P", "S": "S"}

# Reflection phase -> `(descending wave, ascending wave)` about the CMB.
_REFLECTION_PHASES: dict[str, tuple[Wave, Wave]] = {
    "PcP": ("P", "P"),
    "ScS": ("S", "S"),
    "PcS": ("P", "S"),
    "ScP": ("S", "P"),
}

# Every phase the dispatch below handles. `Phase` is the same set as a
# static type; `test_phase_literal_matches_dispatch_tables` locks the two
# together.
_SUPPORTED_PHASES: frozenset[str] = frozenset(
    _TURNING_PHASES.keys() | _REFLECTION_PHASES.keys()
)

# Velocity models with a bundled `.tvel` file;
# `test_model_literal_matches_bundled_tvel_files` locks this to `Model`.
_SUPPORTED_MODELS: frozenset[str] = frozenset(get_args(Model.__value__))

# Relative margin keeping a solved ray parameter off the exact grazing
# slowness, where the turning integrand vanishes and the integrals
# degenerate.
_GRAZING_MARGIN = 1e-9

# Ceiling on bisection steps per phase. The bracket halves every step, so
# _BISECTION_TOLERANCE is reached well before the ceiling.
_MAX_BISECTION_STEPS = 200

# Ray-parameter bracket width, in seconds per kilometre, at which
# bisection stops.
_BISECTION_TOLERANCE = 1e-15


def _down_going_delta(profile: SlownessProfile, z_s: float, p: float) -> float | None:
    """Epicentral distance (radians) of a down-going turning ray, or `None`.

    Args:
        profile: The slowness profile the ray propagates in.
        z_s: Flattened source depth, in kilometres.
        p: Ray parameter, in seconds per kilometre.

    Returns:
        The epicentral distance in radians, or `None` when the ray has no
        turning point below the source.
    """
    result = profile.direct_time(z_s, p)
    if result is None:
        return None
    return result[1] / _EARTH_RADIUS_KM


def _bisect_ray_parameter(
    delta_of_p: Callable[[float], float | None],
    target: float,
    lo: float,
    hi: float,
) -> float | None:
    """Ray parameter in `[lo, hi]` whose ray reaches epicentral distance *target*.

    *delta_of_p* maps a ray parameter to the epicentral distance its ray
    covers, and must be monotonic across the bracket, with the root of
    `delta_of_p(p) == target` lying inside `[lo, hi]` (the caller checks
    this). If it returns `None` at any step the ray has been lost and the
    search returns `None`.

    Args:
        delta_of_p: Epicentral distance in radians as a function of ray
            parameter in seconds per kilometre.
        target: Epicentral distance to solve for, in radians.
        lo: Lower end of the ray-parameter bracket, in seconds per kilometre.
        hi: Upper end of the ray-parameter bracket, in seconds per kilometre.

    Returns:
        The solved ray parameter in seconds per kilometre, or `None` if
        *delta_of_p* returned `None` during the search.
    """
    reference = delta_of_p(lo)
    if reference is None:
        return None
    delta_decreases_with_p = reference > target
    for _ in range(_MAX_BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        value = delta_of_p(mid)
        if value is None:
            return None
        if (value > target) == delta_decreases_with_p:
            lo = mid
        else:
            hi = mid
        if hi - lo < _BISECTION_TOLERANCE:
            break
    return 0.5 * (lo + hi)


def _travel_time(
    profile: SlownessProfile, z_s: float, z_cmb: float, dist: float
) -> float | None:
    """Travel time of a turning-ray phase at source depth *z_s* and distance *dist*.

    Returns `None` when no down-going ray turns at the requested distance,
    either because the distance falls in the core shadow or because it is
    below the closest down-going arrival (see the module docstring).

    The ray-parameter range is split at the profile's branch knots so that
    epicentral distance is monotonic on each sub-range. Where an
    upper-mantle triplication makes several rays reach *dist*, each is
    solved and the earliest arrival returned.

    Args:
        profile: The slowness profile of the phase.
        z_s: Flattened source depth, in kilometres.
        z_cmb: Flattened core–mantle boundary depth, in kilometres.
        dist: Epicentral distance, in radians.

    Returns:
        Travel time in seconds, or `None` when no down-going ray reaches
        *dist*.
    """
    p_min = profile.u_at(z_cmb) * (1 + _GRAZING_MARGIN)
    p_max = profile.u_at(z_s) * (1 - _GRAZING_MARGIN)
    if p_min >= p_max:
        return None  # source at the CMB: no room for a turning ray

    def turning_delta(p: float) -> float | None:
        return _down_going_delta(profile, z_s, p)

    knots = profile.branch_knots
    bounds = [p_min, *knots[(knots > p_min) & (knots < p_max)], p_max]

    earliest: float | None = None
    for index, (lo, hi) in enumerate(pairwise(bounds)):
        # Nudge off the interior knots, where the turning integrand grazes.
        p_lo = lo if index == 0 else lo * (1 + _GRAZING_MARGIN)
        p_hi = hi if index == len(bounds) - 2 else hi * (1 - _GRAZING_MARGIN)
        d_lo = turning_delta(p_lo)
        d_hi = turning_delta(p_hi)
        if d_lo is None or d_hi is None or (d_lo - dist) * (d_hi - dist) >= 0.0:
            continue
        p = _bisect_ray_parameter(turning_delta, dist, p_lo, p_hi)
        if p is None:
            continue
        result = profile.direct_time(z_s, p)
        if result is not None and (earliest is None or result[0] < earliest):
            earliest = result[0]
    return earliest


def _reflect_time(
    profile_down: SlownessProfile,
    profile_up: SlownessProfile,
    z_s: float,
    z_cmb: float,
    dist: float,
) -> float | None:
    """Travel time of a core–mantle boundary reflection, or `None`.

    The ray descends in *profile_down* from the source to the CMB and
    rises in *profile_up* to the surface, allowing conversion between P
    and S at the reflector (PcP, ScS, PcS, ScP). The ray parameter is
    bounded above by the lower of the two waves' boundary slownesses,
    below which the reflected ray's distance rises from zero, so the
    branch supports every distance up to the CMB grazing limit and is
    solved by bisection.

    Returns `None` for distances beyond that limit (the core shadow),
    where no reflected ray exists.

    Args:
        profile_down: Slowness profile of the descending wave leg.
        profile_up: Slowness profile of the ascending wave leg.
        z_s: Flattened source depth, in kilometres.
        z_cmb: Flattened core–mantle boundary depth, in kilometres.
        dist: Epicentral distance, in radians.

    Returns:
        Travel time in seconds, or `None` when the reflected ray's
        distance exceeds the CMB grazing limit.
    """
    p_hi = min(profile_down.u_at(z_cmb), profile_up.u_at(z_cmb)) * (1 - _GRAZING_MARGIN)

    def reflect_delta_tau(p: float) -> tuple[float, float]:
        tau_s, delta_s = profile_down.integrate(z_s, p)
        tau_down, delta_down = profile_down.integrate(z_cmb, p)
        tau_up, delta_up = profile_up.integrate(z_cmb, p)
        tau = (tau_down - tau_s) + tau_up
        delta = (delta_down - delta_s) + delta_up
        return tau, delta

    def reflect_delta(p: float) -> float:
        return reflect_delta_tau(p)[1] / _EARTH_RADIUS_KM

    if not (0.0 < dist < reflect_delta(p_hi)):
        return None
    p = _bisect_ray_parameter(reflect_delta, dist, 0.0, p_hi)
    if p is None:
        return None
    tau, delta = reflect_delta_tau(p)
    return tau + p * delta


def solve(
    depth_km: float,
    dist_deg: float,
    phases: Sequence[Phase],
    model: Model = "iasp91",
) -> dict[str, float]:
    """Tau-p travel times for a source–receiver geometry, in seconds.

    Internal core for [`pysmo.tools.traveltime.travel_times`][]; works in
    kilometres and degrees.

    Args:
        depth_km: Source depth in kilometres.
        dist_deg: Epicentral distance in degrees.
        phases: Seismic phase names to compute.
        model: Velocity model.

    Returns:
        Mapping of phase name to travel time in seconds. Phases without an
        arrival at the given geometry (e.g. upcoming Pn/regional
        distances, or the core shadow) are omitted.

    Raises:
        ValueError: If *model* is not a supported model, *phases* contains
            an unsupported phase name, *depth_km* is outside the surface
            to core–mantle boundary range, or *dist_deg* is outside 0 to
            180 degrees.

    Note:
        Turning phases (P, S) return the first arrival: the search is
        split at the model's velocity discontinuities, so an upper-mantle
        triplication resolves to its earliest branch. A triplication from
        a smooth velocity gradient with no discontinuity is not split and
        may return a later branch.
    """
    if model not in _SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported velocity model {model!r}; supported models: "
            + f"{sorted(_SUPPORTED_MODELS)!r}."
        )
    unknown = sorted(phase for phase in phases if phase not in _SUPPORTED_PHASES)
    if unknown:
        raise ValueError(
            f"Unsupported phase(s) {unknown!r}; supported phases: "
            + f"{sorted(_SUPPORTED_PHASES)!r}."
        )
    cmb_km = cmb_depth_km(model)
    if not 0.0 <= depth_km <= cmb_km:
        raise ValueError(
            f"Source depth {depth_km} km is outside the modelled range "
            + f"0 to {cmb_km:.1f} km (surface to core–mantle boundary)."
        )
    if not 0.0 <= dist_deg <= 180.0:
        raise ValueError(
            f"Epicentral distance {dist_deg} degrees is outside the range "
            + "0 to 180 degrees."
        )
    z_s = _flattened_depth(depth_km)
    z_cmb = _flattened_depth(cmb_km)
    dist = math.radians(dist_deg)
    arrivals: dict[str, float] = {}
    for phase in phases:
        if phase in _TURNING_PHASES:
            wave = _TURNING_PHASES[phase]
            time = _travel_time(get_profile(model, wave), z_s, z_cmb, dist)
        else:
            down_wave, up_wave = _REFLECTION_PHASES[phase]
            time = _reflect_time(
                get_profile(model, down_wave),
                get_profile(model, up_wave),
                z_s,
                z_cmb,
                dist,
            )
        if time is not None:
            arrivals[phase] = time
    return arrivals
