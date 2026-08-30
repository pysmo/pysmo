"""Predicted body-wave travel times.

[`travel_times`][pysmo.tools.traveltime.travel_times] is the default
source of predicted arrivals wherever pysmo needs them. It computes each
arrival by integrating a velocity model included with pysmo, on every
call rather than from precomputed tables. This is precise and fast enough
for simple tasks, but it does not scale to bulk work, and it covers only
the models in [`Model`][pysmo.tools.traveltime.Model] and the phases in
[`Phase`][pysmo.tools.traveltime.Phase].

[`travel_times`][pysmo.tools.traveltime.travel_times] can be substituted
with any function that takes the same arguments and returns the same
type. [`TravelTimeBackend`][pysmo.tools.traveltime.TravelTimeBackend]
describes that shape.

Depth is in metres, epicentral distance in degrees, travel times are
[`pandas.Timedelta`][].
"""

from collections.abc import Sequence
from functools import partial

import pandas as pd

from pysmo.tools.traveltime._solver import solve
from pysmo.tools.traveltime._types import Model, Phase, TravelTimeBackend

__all__ = ["Model", "Phase", "TravelTimeBackend", "travel_times"]


def travel_times(
    *,
    depth: float,
    distance: float,
    phases: Sequence[Phase],
    model: Model = "iasp91",
) -> dict[str, pd.Timedelta]:
    """Predicted travel times for a source–receiver geometry.

    Computed by integrating an included velocity model.

    Args:
        depth: Source depth in metres, positive downwards.
        distance: Epicentral distance in degrees.
        phases: Phase names to compute.
        model: Velocity model.

    Returns:
        Mapping of phase name to travel time. Phases with no arrival at
        the given geometry are omitted.

    Raises:
        ValueError: If *model* is not a supported model, *phases* contains
            an unsupported phase name, *depth* is outside the surface to
            core–mantle boundary range, or *distance* is outside 0 to 180
            degrees.

    Note:
        Each phase is solved on a single turning branch. Where the model
        produces a travel-time triplication — mainly P and S at short
        distances for a shallow source — that branch need not be the
        first arrival.

    Examples:
        `P` and `S` for a 22.9 km deep source at 60°:

        ```python
        >>> from pysmo.tools.traveltime import travel_times
        >>> tt = travel_times(depth=22900.0, distance=60.0, phases=["P", "S"])
        >>> {phase: round(t.total_seconds(), 2) for phase, t in tt.items()}
        {'P': 604.65, 'S': 1096.55}
        >>>
        ```

        A phase-relative fetch window, via
        [`haversine`][pysmo.tools.azdist.haversine] and a class's
        `.fetch()` (e.g.
        [`GeoCsvSeismogram.fetch`][pysmo.classes.GeoCsvSeismogram.fetch]):

        ```python
        >>> import pandas as pd
        >>> from pysmo import MiniEvent, MiniStation
        >>> from pysmo.classes import GeoCsvSeismogram
        >>> from pysmo.tools.azdist import haversine
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> event = MiniEvent(
        ...     latitude=-36.122, longitude=-72.898, depth=22900.0,
        ...     time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
        ... )
        >>> dist = haversine(event, station)
        >>> arrivals = travel_times(depth=event.depth, distance=dist, phases=["P"])
        >>> predicted_p = event.time + arrivals["P"]
        >>>
        ```

        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> seismogram = GeoCsvSeismogram.fetch(
        ...     station=station,
        ...     starttime=predicted_p - pd.Timedelta(minutes=2),
        ...     endtime=predicted_p + pd.Timedelta(minutes=8),
        ... )
        >>>
        ```
        <!-- skip: end -->
    """
    seconds = solve(depth / 1000.0, distance, phases, model=model)
    return {phase: pd.Timedelta(seconds=value) for phase, value in seconds.items()}


# `travel_times` is stricter than `TravelTimeBackend` — its `phases` is the
# `Phase` literal, not plain `str` — so it does not satisfy the protocol
# directly. An argument-free `partial` does, with no behaviour change:
# unknown phase names still raise from `travel_times`. Pickles as a
# reference to `travel_times` (a public, stable symbol), so a saved
# `PysmoProject` on the default backend unpickles as long as that exists.
builtin_backend: TravelTimeBackend = partial(travel_times)
