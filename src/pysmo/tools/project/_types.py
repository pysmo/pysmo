"""Result and callable-seam types shared across the project tool.

[`PysmoProject`][pysmo.tools.project.PysmoProject] has three pluggable
seams, each a plain callable:

- [`WindowResolver`][pysmo.tools.project.WindowResolver] turns an entry into
  an absolute fetch window.
- [`SeismogramFetcher`][pysmo.tools.project.SeismogramFetcher] downloads a
  trace for a station and window.
- [`SeismogramTransform`][pysmo.tools.project.SeismogramTransform] converts a
  downloaded trace into the project's target type.

Each is a `Callable` type alias rather than a `Protocol`: none of the call
shapes needs keyword-only parameters or non-`__call__` attributes, and
[`PhaseWindow`][pysmo.tools.project.PhaseWindow] already ships as a concrete
`WindowResolver` to copy.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from attrs import define

from pysmo import Event, Seismogram, Station

from ._entry import ProjectEntry

__all__ = [
    "FetchContext",
    "SeismogramFetcher",
    "SeismogramTransform",
    "WindowResolver",
    "WindowResult",
]


@define(kw_only=True, frozen=True)
class WindowResult:
    """The absolute fetch window resolved for one entry.

    Returned by a [`WindowResolver`][pysmo.tools.project.WindowResolver].
    """

    starttime: pd.Timestamp
    """Absolute start of the window."""

    endtime: pd.Timestamp
    """Absolute end of the window."""

    reference: pd.Timestamp | None
    """Timestamp the window was placed around (a predicted phase arrival for
    [`PhaseWindow`][pysmo.tools.project.PhaseWindow]), or `None` when the
    window came from an entry's explicit `starttime`/`endtime`."""


@define(kw_only=True, frozen=True)
class FetchContext[TStation: Station, TEvent: Event]:
    """Context passed to `seismogram_transform` with the downloaded seismogram.

    Bundles the originating [`ProjectEntry`][pysmo.tools.project.ProjectEntry]
    with what this specific fetch resolved but that doesn't belong on
    `ProjectEntry` itself. Recomputed fresh on every fetch, never persisted
    (unlike `entry.checksum`, which is deliberately pinned).

    Note the deliberate naming overlap with `entry.starttime`/`entry.endtime`:
    those are the entry's possibly-`None` *explicit override* (see
    [`ProjectEntry`][pysmo.tools.project.ProjectEntry]), while
    `starttime`/`endtime` here are always-populated and reflect the window
    that was *actually used*: identical to the entry's own when an explicit
    override was given, resolved by the project's `window` otherwise. A
    transform wanting "the window this fetch actually covered" should read
    `context.starttime`/`context.endtime`, not
    `context.entry.starttime`/`context.entry.endtime`.
    """

    entry: ProjectEntry[TStation, TEvent]
    """The entry this seismogram was fetched for."""

    starttime: pd.Timestamp
    """Absolute start of the window actually used for this fetch."""

    endtime: pd.Timestamp
    """Absolute end of the window actually used for this fetch."""

    reference: pd.Timestamp | None
    """Timestamp the window was placed around (a predicted phase arrival for
    the default `window`), or `None` if `entry.starttime`/`entry.endtime`
    were used directly."""


type WindowResolver[TStation: Station, TEvent: Event] = Callable[
    [ProjectEntry[TStation, TEvent]], WindowResult
]
"""Resolve an entry's absolute fetch window.

Called with a single [`ProjectEntry`][pysmo.tools.project.ProjectEntry] and
returns a [`WindowResult`][pysmo.tools.project.WindowResult]. Raises
`ValueError` when no window can be resolved (no predicted arrival for the
station/event geometry, or a required event missing).

Only ever called for entries *without* an explicit `starttime`/`endtime`
pair: [`PysmoProject`][pysmo.tools.project.PysmoProject] resolves that case
itself before consulting the resolver, so a custom resolver never has to
reimplement it. [`PhaseWindow`][pysmo.tools.project.PhaseWindow] is the
default. Must be picklable by reference (a top-level function, or an attrs
instance with only picklable fields, not a lambda or closure), the same
constraint as the other two seams.
"""

type SeismogramFetcher = Callable[[Station, pd.Timestamp, pd.Timestamp], Seismogram]
"""Download a seismogram for a station and absolute time window.

Called with a [`Station`][pysmo.Station] and the resolved
`starttime`/`endtime`, and returns a [`Seismogram`][pysmo.Seismogram].
"Always fresh" by contract: [`PysmoProject`][pysmo.tools.project.PysmoProject]
keeps its own in-memory cache, so a fetcher normally hits the network every
time rather than consulting a cache of its own. Swap in a
[`FetchCache`][pysmo.tools.cache.FetchCache] for a reproducible on-disk
cache instead. Must be picklable by reference.
"""

type SeismogramTransform[TStation: Station, TEvent: Event, TSeismogram] = Callable[
    [Seismogram, FetchContext[TStation, TEvent]], TSeismogram
]
"""Convert a freshly downloaded seismogram into the project's target type.

Called with the downloaded [`Seismogram`][pysmo.Seismogram] and a
[`FetchContext`][pysmo.tools.project.FetchContext] carrying the originating
entry and this fetch's resolved window. The one place ordinary data
preparation (response removal, detrending, resampling) belongs, and free to
issue its own additional fetches (e.g. instrument response metadata via
[`StationXML.fetch`][pysmo.classes.StationXML.fetch]). Must be picklable by
reference. Wrap it in a
[`TransformCache`][pysmo.tools.project.TransformCache] to cache its output
(and those additional fetches) on disk.
"""
