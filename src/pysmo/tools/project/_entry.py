"""The ProjectEntry class and the build_entries helper."""

from collections.abc import Callable, Iterable

import pandas as pd
from attrs import converters, define, field, setters

from pysmo import Event, Station
from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = ["ProjectEntry", "build_entries"]


@define(kw_only=True)
class ProjectEntry[TStation: Station, TEvent: Event = Event]:
    """One station/event selection within a [`PysmoProject`][pysmo.tools.project.PysmoProject].

    Pairs a station with either an event (for a phase-arrival-relative
    window, resolved at fetch time) or an explicit absolute time window
    (for event-less or continuous data), or both — an explicit window
    always takes precedence over one derived from `event`. See
    [`PysmoProject`][pysmo.tools.project.PysmoProject] for how the window is
    actually resolved.

    Generic over the station and event types it was built with, so a
    [`PysmoProject`][pysmo.tools.project.PysmoProject] built from a list of
    entries keeps those concrete types (e.g. `project.events` comes back as
    `list[QuakeML]`, not `list[Event]`). An event-less entry leaves `TEvent`
    at its default, [`Event`][pysmo.Event]. A list mixing event-bearing and
    event-less entries has no single inferred element type — annotate it
    (`list[ProjectEntry[MyStation, MyEvent]]`) or reach for
    [`build_entries`][pysmo.tools.project.build_entries], which produces a
    homogeneous list.
    """

    station: TStation
    """Station to fetch waveform data for."""

    event: TEvent | None = None
    """Event used to derive a phase-arrival-relative window, if `starttime`/`endtime` are not set."""

    starttime: pd.Timestamp | None = field(
        default=None,
        converter=converters.optional(convert_to_utc_timestamp),
        on_setattr=setters.convert,
    )
    """Explicit start of the fetch window (UTC). Overrides `event` when set together with `endtime`."""

    endtime: pd.Timestamp | None = field(
        default=None,
        converter=converters.optional(convert_to_utc_timestamp),
        on_setattr=setters.convert,
    )
    """Explicit end of the fetch window (UTC). Overrides `event` when set together with `starttime`."""

    checksum: str | None = field(default=None)
    """Checksum of the fetched seismogram, set on first fetch; `None` until then.

    A mismatch on a later fetch means the underlying archive data changed
    since this entry was first fetched — see
    [`PysmoProject.on_checksum_mismatch`][pysmo.tools.project.PysmoProject.on_checksum_mismatch]
    for how that is reported. Deliberately mutated by
    [`PysmoProject`][pysmo.tools.project.PysmoProject] as a side effect of
    fetching, so it is captured the next time the containing project is
    pickled — this is what makes it a durable reproducibility pin rather
    than a one-session-only check.

    Because this field is mutated in place, a `ProjectEntry` shared across
    two different `PysmoProject` instances (e.g. reused deliberately in an
    iterative workflow, or accidentally via a shared `entries` list) has its
    checksum set/checked by *whichever* project fetches it first — the
    entry doesn't belong to one project. Sharing entries across projects is
    fine; sharing them without being aware their checksum state is joint,
    not per-project, is the surprise to avoid.
    """


def build_entries[TStation: Station, TEvent: Event](
    stations: Iterable[TStation],
    events: Iterable[TEvent],
    predicate: Callable[[TStation, TEvent], bool] | None = None,
) -> list[ProjectEntry[TStation, TEvent]]:
    """Build project entries from a filtered cross product of stations and events.

    One [`ProjectEntry`][pysmo.tools.project.ProjectEntry] per (station,
    event) pair for which `predicate` returns `True` — every pair if
    `predicate` is `None`. `stations` and `events` are expected to be
    already narrowed to the working set; this function pairs, it does not
    narrow or transform.

    Args:
        stations: The stations to pair, already narrowed.
        events: The events to pair, already narrowed.
        predicate: Optional `(station, event) -> bool` deciding which pairs
            become entries. Called eagerly and not stored, so a lambda or
            closure is fine. The dominant use is a distance cutoff, e.g.
            `lambda s, e: haversine(e, s) <= 95.0`.

    Returns:
        One `ProjectEntry` per surviving pair, stations-outer / events-inner.
    """
    stations = list(stations)
    events = list(events)
    return [
        ProjectEntry(station=station, event=event)
        for station in stations
        for event in events
        if predicate is None or predicate(station, event)
    ]
