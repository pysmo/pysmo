"""The ProjectEntry class."""

import pandas as pd
from attrs import converters, define, field, setters

from pysmo import Event, Station
from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = ["ProjectEntry"]


@define(kw_only=True)
class ProjectEntry:
    """One station/event selection within a [`PysmoProject`][pysmo.tools.project.PysmoProject].

    Pairs a station with either an event (for a phase-arrival-relative
    window, resolved at fetch time) or an explicit absolute time window
    (for event-less or continuous data), or both — an explicit window
    always takes precedence over one derived from `event`. See
    [`PysmoProject`][pysmo.tools.project.PysmoProject] for how the window is
    actually resolved.
    """

    station: Station
    """Station to fetch waveform data for."""

    event: Event | None = None
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
