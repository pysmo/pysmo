"""The PhaseWindow resolver: a window placed around a predicted phase arrival."""

from __future__ import annotations

import pandas as pd
from attrs import define, field, validators

from pysmo import Event, Station
from pysmo.lib.validators import convert_to_timedelta
from pysmo.tools.azdist import haversine
from pysmo.tools.traveltime import TravelTimeBackend, builtin_backend
from pysmo.typing import NonPositiveTimedelta, PositiveTimedelta

from ._entry import ProjectEntry
from ._types import WindowResult

__all__ = ["PhaseWindow"]


@define(kw_only=True, frozen=True)
class PhaseWindow:
    """Resolve a fetch window from an entry's event and a predicted phase arrival.

    The default [`WindowResolver`][pysmo.tools.project.WindowResolver] for
    [`PysmoProject`][pysmo.tools.project.PysmoProject]: predicts the `phase`
    arrival for the station/event geometry with `travel_time_backend`, then
    returns the window `[arrival + pre_pick, arrival + post_pick]`.

    Frozen and picklable by value (given a picklable `travel_time_backend`),
    so it travels with a pickled `PysmoProject`.
    """

    phase: str = field(default="P")
    """Seismic phase the window is placed around.

    With the default `travel_time_backend` this must be one of the phases in
    [`Phase`][pysmo.tools.traveltime.Phase]; any other name raises when a
    window is resolved. A custom backend may accept a wider set.
    """

    pre_pick: NonPositiveTimedelta = field(
        default=pd.Timedelta(minutes=-2),
        converter=convert_to_timedelta,
        validator=[
            validators.instance_of(pd.Timedelta),
            validators.le(pd.Timedelta(0)),
        ],
    )
    """Offset from the predicted arrival to the window start; zero or negative."""

    post_pick: PositiveTimedelta = field(
        default=pd.Timedelta(minutes=8),
        converter=convert_to_timedelta,
        validator=[
            validators.instance_of(pd.Timedelta),
            validators.gt(pd.Timedelta(0)),
        ],
    )
    """Offset from the predicted arrival to the window end. Must be positive."""

    travel_time_backend: TravelTimeBackend = field(default=builtin_backend)
    """Predicts the phase arrival the window is built around.

    Defaults to pysmo's built-in solver,
    [`travel_times`][pysmo.tools.traveltime.travel_times]. Replace it with
    any callable of the same shape
    ([`TravelTimeBackend`][pysmo.tools.traveltime.TravelTimeBackend]) for
    another velocity model, a phase the built-in solver does not cover, or
    arrival times from an external source. Must be picklable: a top-level
    function, a [`functools.partial`][] of one, or an attrs instance with
    only picklable fields; not a lambda or closure.
    """

    def __call__[TS: Station, TE: Event](
        self, entry: ProjectEntry[TS, TE]
    ) -> WindowResult:
        """Resolve the window for `entry`.

        Raises:
            ValueError: If `entry` has no event, or no `phase` arrival is
                predicted for its station/event geometry.
        """
        if entry.event is None:
            raise ValueError(
                "PhaseWindow needs an entry with an event to derive a window."
            )
        distance = haversine(entry.event, entry.station)
        arrivals = self.travel_time_backend(
            depth=entry.event.depth, distance=distance, phases=[self.phase]
        )
        if self.phase not in arrivals:
            raise ValueError(
                f"No {self.phase!r} arrival predicted for "
                + f"{entry.station.network}.{entry.station.name} at this "
                + "distance/depth."
            )
        reference = entry.event.time + arrivals[self.phase]
        return WindowResult(
            starttime=reference + self.pre_pick,
            endtime=reference + self.post_pick,
            reference=reference,
        )
