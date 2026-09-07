"""The ProjectEntry class and the build_entries helper."""

from collections.abc import Callable, Iterable
from typing import Any

import pandas as pd
from attrs import converters, define, field, setters

from pysmo import Event, Station
from pysmo.lib.validators import convert_to_utc_timestamp

from ._identity import entry_identity, entry_identity_components

__all__ = ["ProjectEntry", "build_entries"]


@define(kw_only=True)
class ProjectEntry[TStation: Station, TEvent: Event = Event]:
    """One station/event selection within a `PysmoProject`.

    Pairs a station with either an event (for a phase-arrival-relative
    window, resolved at fetch time) or an explicit absolute time window
    (for event-less or continuous data), or both; an explicit window
    always takes precedence over one derived from `event`. See
    [`PysmoProject`][pysmo.tools.project.PysmoProject] for how the window is
    actually resolved.

    At least one of (`event`, an explicit `starttime`/`endtime` pair) is
    required; a lone `starttime` or `endtime`, or a `starttime` at or after
    `endtime`, raises `ValueError` at construction.

    Generic over the station and event types it was built with, so a
    [`PysmoProject`][pysmo.tools.project.PysmoProject] built from a list of
    entries keeps those concrete types (e.g. `project.events` comes back as
    `list[QuakeML]`, not `list[Event]`). An event-less entry leaves `TEvent`
    at its default, [`Event`][pysmo.Event]. A list mixing event-bearing and
    event-less entries has no single inferred element type, so annotate it
    (`list[ProjectEntry[MyStation, MyEvent]]`) or reach for
    [`build_entries`][pysmo.tools.project.build_entries], which produces a
    homogeneous list.
    """

    station: TStation
    """Station to fetch waveform data for."""

    event: TEvent | None = None
    """Event for deriving a phase-arrival-relative window (if no explicit times)."""

    starttime: pd.Timestamp | None = field(
        default=None,
        converter=converters.optional(convert_to_utc_timestamp),
        on_setattr=setters.convert,
    )
    """Explicit start of the fetch window (UTC).

    Overrides `event` when set together with `endtime`.
    """

    endtime: pd.Timestamp | None = field(
        default=None,
        converter=converters.optional(convert_to_utc_timestamp),
        on_setattr=setters.convert,
    )
    """Explicit end of the fetch window (UTC).

    Overrides `event` when set together with `starttime`.
    """

    checksum: str | None = field(default=None)
    """Checksum of the fetched seismogram, set on first fetch; `None` until then.

    A mismatch on a later fetch means the underlying archive data changed
    since this entry was first fetched; see
    [`PysmoProject.on_checksum_mismatch`][pysmo.tools.project.PysmoProject.on_checksum_mismatch]
    for how that is reported. Deliberately mutated by
    [`PysmoProject`][pysmo.tools.project.PysmoProject] as a side effect of
    fetching, so it is captured the next time the containing project is
    pickled; this is what makes it a durable reproducibility pin rather
    than a one-session-only check.

    Because this field is mutated in place, a `ProjectEntry` shared across
    two different `PysmoProject` instances (e.g. reused deliberately in an
    iterative workflow, or accidentally via a shared `entries` list) has its
    checksum set/checked by *whichever* project fetches it first; the
    entry doesn't belong to one project. Sharing entries across projects is
    fine; sharing them without being aware their checksum state is joint,
    not per-project, is the surprise to avoid.
    """

    @property
    def identity_components(self) -> dict[str, Any]:
        """This entry's normalised natural key as a nested dict, before hashing.

        Examples:
            >>> import pandas as pd
            >>> from pysmo import MiniEvent, MiniStation
            >>> from pysmo.tools.project import ProjectEntry
            >>> station = MiniStation(
            ...     name="ANMO",
            ...     network="IU",
            ...     location="00",
            ...     channel="BHZ",
            ...     latitude=34.9459,
            ...     longitude=-106.4571,
            ... )
            >>> event = MiniEvent(
            ...     latitude=-36.122,
            ...     longitude=-72.898,
            ...     depth=22900.0,
            ...     time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
            ... )
            >>> entry = ProjectEntry(station=station, event=event)
            >>> components = entry.identity_components
            >>> components["schema"]
            'v1'
            >>> components["station"]["name"]
            'ANMO'
        """
        return entry_identity_components(self)

    @property
    def identity(self) -> str:
        """Stable identity string for this entry, computed without fetching.

        Derived from the natural key: `'v1:'` and a sha256 hexdigest. Persist it
        and pass it to
        [`PysmoProject.get`][pysmo.tools.project.PysmoProject.get] to retrieve
        the entry's seismogram later.

        Examples:
            >>> import pandas as pd
            >>> from pysmo import MiniEvent, MiniStation
            >>> from pysmo.tools.project import ProjectEntry
            >>> station = MiniStation(
            ...     name="ANMO",
            ...     network="IU",
            ...     location="00",
            ...     channel="BHZ",
            ...     latitude=34.9459,
            ...     longitude=-106.4571,
            ... )
            >>> event = MiniEvent(
            ...     latitude=-36.122,
            ...     longitude=-72.898,
            ...     depth=22900.0,
            ...     time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
            ... )
            >>> entry = ProjectEntry(station=station, event=event)
            >>> entry.identity.startswith("v1:")
            True
            >>> len(entry.identity)
            67
        """
        return entry_identity(self)

    def __attrs_post_init__(self) -> None:
        """Reject a half-specified, reversed, or (event-less) absent window."""
        if (self.starttime is None) != (self.endtime is None):
            raise ValueError(
                "ProjectEntry needs both starttime and endtime, or neither."
            )
        if (
            self.starttime is not None
            and self.endtime is not None
            and self.starttime >= self.endtime
        ):
            raise ValueError("ProjectEntry starttime must be before endtime.")
        if self.event is None and self.starttime is None:
            raise ValueError(
                "ProjectEntry needs an explicit starttime/endtime window or an "
                + "event to derive one from."
            )


def build_entries[TStation: Station, TEvent: Event](
    stations: Iterable[TStation],
    events: Iterable[TEvent],
    predicate: Callable[[TStation, TEvent], bool] | None = None,
) -> list[ProjectEntry[TStation, TEvent]]:
    """Build project entries from a filtered cross product of stations and events.

    One [`ProjectEntry`][pysmo.tools.project.ProjectEntry] per (station,
    event) pair for which `predicate` returns `True`, or every pair if
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
