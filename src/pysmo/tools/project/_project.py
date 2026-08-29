"""The PysmoProject class and functions used within the class."""

import hashlib
import threading
import warnings
from collections.abc import Callable
from typing import Any, Literal

import pandas as pd
from attrs import Attribute, define, field, setters, validators

from pysmo import Event, MiniSeismogram, Seismogram, Station
from pysmo._utils import attrs_getstate, attrs_setstate
from pysmo.classes import MSeed
from pysmo.functions import clone_to_mini
from pysmo.lib.validators import convert_to_timedelta
from pysmo.tools.azdist import haversine
from pysmo.tools.web import TravelTimeBackend, fetch_travel_times
from pysmo.typing import NonPositiveTimedelta, PositiveTimedelta

from ._entry import ProjectEntry

__all__ = ["FetchContext", "PysmoProject"]


def _default_fetch_seismogram(
    station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> Seismogram:
    """Default `fetch_seismogram` implementation for [`PysmoProject`][pysmo.tools.project.PysmoProject].

    Fetches and parses a waveform from the EarthScope FDSN dataselect
    service as miniSEED, via [`MSeed.fetch`][pysmo.classes.MSeed.fetch].
    """
    return MSeed.fetch(station=station, starttime=starttime, endtime=endtime)


def _seismogram_to_mini_seismogram(
    seismogram: Seismogram, context: "FetchContext"
) -> MiniSeismogram:
    """Default `seismogram_transform`: the raw downloaded trace as a `MiniSeismogram`.

    No processing — response removal, detrending and the like stay an
    explicit opt-in via a custom `seismogram_transform`.
    """
    return clone_to_mini(MiniSeismogram, seismogram)


def _checksum(seismogram: Seismogram) -> str:
    """Checksum a freshly downloaded seismogram, before `seismogram_transform` runs.

    Hashed pre-transform deliberately: the transform's output (e.g. a
    `MiniIccsSeismogram`) can be mutated downstream by whatever consumes it
    (`ICCS` changes `t0`/`t1`/`flip`/`select` during a run) — hashing after
    the transform would pick up that unrelated mutation as false "drift".
    """
    h = hashlib.sha256()
    h.update(seismogram.data.tobytes())
    h.update(str(seismogram.begin_time).encode())
    h.update(str(seismogram.delta).encode())
    return f"sha256:{h.hexdigest()}"


def _on_setattr_clear_cache[T](
    instance: "PysmoProject", attribute: Attribute, value: T
) -> T:
    """Setter that clears the fetch cache when a parameter affecting it changes."""
    if (current := getattr(instance, attribute.name)) is value:
        return value
    if (current == value) is True:
        return value
    instance.clear_cache()
    return value


@define(kw_only=True, frozen=True)
class FetchContext:
    """Context handed to `seismogram_transform` alongside the freshly downloaded seismogram.

    Bundles the originating [`ProjectEntry`][pysmo.tools.project.ProjectEntry]
    with what this specific fetch resolved but that doesn't belong on
    `ProjectEntry` itself — recomputed fresh on every fetch, never
    persisted (unlike `entry.checksum`, which is deliberately pinned).

    Note the deliberate naming overlap with `entry.starttime`/`entry.endtime`:
    those are the entry's possibly-`None` *explicit override* (see
    [`ProjectEntry`][pysmo.tools.project.ProjectEntry]), while
    `starttime`/`endtime` here are always-populated and reflect the window
    that was *actually used* — identical to the entry's own when an explicit
    override was given, resolved from `predicted` otherwise. A transform
    wanting "the window this fetch actually covered" should read
    `context.starttime`/`context.endtime`, not
    `context.entry.starttime`/`context.entry.endtime`.
    """

    entry: ProjectEntry[Any, Any]
    """The entry this seismogram was fetched for."""

    starttime: pd.Timestamp
    """Absolute start of the window actually used for this fetch."""

    endtime: pd.Timestamp
    """Absolute end of the window actually used for this fetch."""

    predicted: pd.Timestamp | None
    """Predicted phase arrival used to derive the window, or `None` if
    `entry.starttime`/`entry.endtime` were used directly."""


type _EventKey = tuple[float, float, float, pd.Timestamp] | None
"""(latitude, longitude, depth, time) — everything `_resolve_window` actually
reads off `Event` (via `haversine` and `entry.event.time`), not just `time`.
Keying on `time` alone would collide two distinct events sharing an origin
time but not a location, since they resolve to different windows via
`haversine`."""

type _CacheKey = tuple[
    str, str, str, str, _EventKey, pd.Timestamp | None, pd.Timestamp | None
]


@define(kw_only=True)
class PysmoProject[TStation: Station, TEvent: Event, TSeismogram = MiniSeismogram]:
    """Declares station/event data to fetch on demand and transform into `TSeismogram`.

    A `PysmoProject` holds a flat list of
    [`ProjectEntry`][pysmo.tools.project.ProjectEntry] objects plus the
    parameters needed to resolve each entry's fetch window and the
    `seismogram_transform` callable that turns a freshly downloaded
    [`Seismogram`][pysmo.Seismogram] into the caller's target type
    `TSeismogram`. No waveform data is stored on the instance between calls
    beyond an in-memory cache of already-fetched-and-transformed results.

    Generic over the station and event types of its `entries` (matching
    [`ProjectEntry`][pysmo.tools.project.ProjectEntry]'s parameter order)
    and the return type of `seismogram_transform`, all three inferred at
    construction: `TStation` / `TEvent` from `entries` (build them with
    [`build_entries`][pysmo.tools.project.build_entries] from a list of, say,
    `StationXML` and `QuakeML`, and `project.stations` / `project.events`
    come back as `list[StationXML]` / `list[QuakeML]`), `TSeismogram` from
    `seismogram_transform`'s return type, defaulting to
    [`MiniSeismogram`][pysmo.MiniSeismogram] when the default transform is
    used.

    See the [module documentation][pysmo.tools.project] for a worked
    example.

    Note: Thread-safety
        The in-memory fetch cache is safe to touch from multiple threads
        calling [`seismogram`][pysmo.tools.project.PysmoProject.seismogram],
        [`seismograms_for`][pysmo.tools.project.PysmoProject.seismograms_for],
        or [`fetch_all`][pysmo.tools.project.PysmoProject.fetch_all] on the
        same instance concurrently. This does not parallelise fetching
        itself, though: `fetch_seismogram` is called outside the lock, so
        two threads racing the same not-yet-cached entry both still fetch
        before one result wins and is cached.

        Reassigning a window parameter (`phase`, `pre_pick`, …) on one
        thread while another is mid-fetch is also safe: the in-flight fetch
        still returns a result, it just isn't cached (the next call
        recomputes it with the current parameters).
    """

    entries: list[ProjectEntry[TStation, TEvent]] = field(
        factory=list, on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache)
    )
    """Station/event/window selections making up this project.

    Build them with
    [`build_entries`][pysmo.tools.project.build_entries]; grow the project
    later with `project.entries.extend(build_entries(...))` (a plain
    in-place mutation — call
    [`clear_cache`][pysmo.tools.project.PysmoProject.clear_cache] afterwards
    only to free memory, never for correctness, since the fetch cache is
    keyed by entry content).
    """

    seismogram_transform: Callable[[Seismogram, FetchContext], TSeismogram] = field(
        # The default returns `MiniSeismogram`, which is `TSeismogram`'s own
        # default, but mypy still can't match a concrete return against the
        # bare type parameter in the class body.
        default=_seismogram_to_mini_seismogram,  # type: ignore[assignment]
        on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache),
    )
    """Applied to a freshly downloaded seismogram; converts the result into the target type `TSeismogram`.

    Called with the downloaded seismogram and a
    [`FetchContext`][pysmo.tools.project.FetchContext] carrying the
    originating entry and this fetch's resolved window/predicted arrival.
    Defaults to returning the raw trace as a
    [`MiniSeismogram`][pysmo.MiniSeismogram] — response removal, detrending
    and resampling are never applied unless a custom transform does so
    explicitly. A custom transform is also where that ordinary data
    preparation belongs, since it is the one place every fetch already
    passes through, and it is free to do anything else it needs — including
    its own additional fetches (e.g. instrument response metadata via
    [`StationXML.fetch`][pysmo.classes.StationXML.fetch],
    demonstrated in the [module documentation][pysmo.tools.project]'s own
    example — this design doesn't fetch or know about response data itself,
    deliberately). Must be a top-level function in an importable module —
    not a lambda or closure — if the containing `PysmoProject` is to be
    pickled; a callable `attrs` class with only picklable fields (same
    example) is the alternative once the transform needs its own
    configuration.
    """

    fetch_seismogram: Callable[[Station, pd.Timestamp, pd.Timestamp], Seismogram] = (
        field(
            default=_default_fetch_seismogram,
            on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache),
        )
    )
    """Downloads a seismogram for a station and absolute time window.

    Defaults to a private helper wrapping
    [`MSeed.fetch`][pysmo.classes.MSeed.fetch] — the explicit "always
    fresh, never cached" choice. The fetched trace is normalised to a
    [`MiniSeismogram`][pysmo.MiniSeismogram] by the default
    `seismogram_transform`, so the project's return type is unchanged by
    the fetch format.

    For any project where reproducibility matters, substitute a
    [`SqliteArchiveFetcher`][pysmo.tools.archive.SqliteArchiveFetcher]
    instance instead — this is the *recommended* value for real analysis
    work, not a power-user option sitting alongside the default on equal
    footing; see its own docstring for why, and how it differs from
    `ProjectEntry.checksum`'s live-fetch drift detection. It only pins the
    waveform, though — see the [module documentation][pysmo.tools.project]'s
    second example for the gotcha this doesn't cover:
    `seismogram_transform` making its own additional fetches. Any other
    callable of the right shape (e.g. one wrapping
    [`SAC.fetch`][pysmo.classes.SAC.fetch]) also works — this field changes
    the retrieval path without subclassing. Must be picklable by reference
    (a top-level function, or an attrs instance with only picklable
    fields — not a lambda or closure), same constraint as `seismogram_transform`.
    """

    phase: str = field(
        default="P", on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache)
    )
    """Seismic phase used to derive a window from an entry's `event`."""

    pre_pick: NonPositiveTimedelta = field(
        default=pd.Timedelta(minutes=-2),
        converter=convert_to_timedelta,
        validator=[
            validators.instance_of(pd.Timedelta),
            validators.le(pd.Timedelta(0)),
        ],
        on_setattr=setters.pipe(
            setters.convert, setters.validate, _on_setattr_clear_cache
        ),
    )
    """Offset from the predicted arrival to the window start. Must be zero or negative."""

    post_pick: PositiveTimedelta = field(
        default=pd.Timedelta(minutes=8),
        converter=convert_to_timedelta,
        validator=[
            validators.instance_of(pd.Timedelta),
            validators.gt(pd.Timedelta(0)),
        ],
        on_setattr=setters.pipe(
            setters.convert, setters.validate, _on_setattr_clear_cache
        ),
    )
    """Offset from the predicted arrival to the window end. Must be positive."""

    travel_time_backend: TravelTimeBackend | None = field(
        default=None, on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache)
    )
    """Optional override for travel-time calculation. See [`pysmo.tools.web.TravelTimeBackend`][]."""

    on_checksum_mismatch: Literal["warn", "raise", "ignore"] = field(
        default="warn",
        validator=validators.in_(("warn", "raise", "ignore")),
    )
    """Behaviour when a fetched seismogram's checksum no longer matches the
    one recorded on `entry.checksum` from its first fetch.

    `"warn"` (default) emits a `UserWarning` and still returns the new data;
    `"raise"` raises `ValueError` instead of returning anything, for a
    pipeline that should hard-stop on detected drift; `"ignore"` returns the
    new data with no signal at all. In every case `entry.checksum` keeps the
    value from the *first* fetch — it is never overwritten by a mismatching
    value, so a mismatch is reported (or not) consistently on every
    subsequent fetch, not just the first time it's noticed.

    Deliberately not part of cache invalidation: changing this policy only
    affects how a *future* mismatch is handled, it doesn't change what data
    was fetched or would be re-fetched, so nothing about previously cached
    results becomes stale when it changes.
    """

    _cache: dict[_CacheKey, tuple[str, TSeismogram]] = field(
        init=False, factory=dict, repr=False, eq=False
    )
    _cache_generation: int = field(init=False, default=0, repr=False, eq=False)
    """Bumped by every `clear_cache()`. A `_fetch` in progress when the cache
    is cleared (e.g. a parameter reassigned on another thread mid-download)
    sees the mismatch and returns its result without caching it under a
    now-stale key."""
    _lock: threading.Lock = field(
        init=False, factory=threading.Lock, repr=False, eq=False
    )
    """Guards reads/writes of `_cache` against concurrent access from more
    than one thread — see the class docstring's thread-safety note."""

    def __getstate__(self) -> dict:
        """Drop the fetch cache and lock, neither of which can survive pickling."""
        state = attrs_getstate(self, {"_cache": {}, "_cache_generation": 0})
        del state["_lock"]
        return state

    def __setstate__(self, state: dict) -> None:
        """Restore state without triggering any `on_setattr` hooks, then create a fresh lock."""
        attrs_setstate(self, state)
        object.__setattr__(self, "_lock", threading.Lock())

    def clear_cache(self) -> None:
        """Clear the in-memory fetch cache.

        Cleared automatically whenever
        [`entries`][pysmo.tools.project.PysmoProject.entries],
        [`seismogram_transform`][pysmo.tools.project.PysmoProject.seismogram_transform],
        [`fetch_seismogram`][pysmo.tools.project.PysmoProject.fetch_seismogram],
        [`phase`][pysmo.tools.project.PysmoProject.phase],
        [`pre_pick`][pysmo.tools.project.PysmoProject.pre_pick],
        [`post_pick`][pysmo.tools.project.PysmoProject.post_pick], or
        [`travel_time_backend`][pysmo.tools.project.PysmoProject.travel_time_backend]
        is *reassigned*.

        Call this manually after any in-place mutation of
        [`entries`][pysmo.tools.project.PysmoProject.entries] (e.g. `append`,
        `remove`, or index assignment), which isn't observable by
        `on_setattr` and therefore doesn't clear the cache automatically.
        """
        with self._lock:
            self._cache.clear()
            self._cache_generation += 1

    def _resolve_window(
        self, entry: ProjectEntry[Any, Any]
    ) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp | None]:
        """Resolve the absolute fetch window and predicted arrival for one entry.

        Returns:
            `(starttime, endtime, predicted_arrival)` — `predicted_arrival`
            is `None` when `entry.starttime`/`entry.endtime` were used
            directly rather than derived from `entry.event`.

        Raises:
            ValueError: If `entry` has neither a usable explicit window nor
                an event to derive one from, or if no `phase` arrival is
                predicted for this station/event geometry.
        """
        if entry.starttime is not None and entry.endtime is not None:
            return entry.starttime, entry.endtime, None
        if entry.event is not None:
            dist = haversine(entry.event, entry.station)
            tt = fetch_travel_times(
                entry.event.depth / 1000.0,
                dist,
                [self.phase],
                travel_time_backend=self.travel_time_backend,
            )
            if self.phase not in tt:
                raise ValueError(
                    f"No {self.phase!r} arrival predicted for "
                    f"{entry.station.network}.{entry.station.name} at this "
                    "distance/depth."
                )
            predicted = entry.event.time + pd.Timedelta(seconds=tt[self.phase])
            return predicted + self.pre_pick, predicted + self.post_pick, predicted
        raise ValueError("ProjectEntry needs either an explicit window or an event.")

    def _fetch(
        self, entry: ProjectEntry[Any, Any], *, _stacklevel: int = 3
    ) -> TSeismogram:
        """Fetch, transform, and cache the seismogram for one entry.

        Internal primitive — see
        [`seismogram`][pysmo.tools.project.PysmoProject.seismogram] for the
        public, station/event-based accessor built on top of this.

        Args:
            entry: The station/event/window selection to fetch.

        Returns:
            The transformed result for `entry`, from cache if this exact
            entry has been fetched before.

        Raises:
            ValueError: If `entry` has neither a usable window nor an event
                (via `_resolve_window`); if the underlying fetch raises
                (e.g. no waveform data for the resolved window); or if the
                checksum no longer matches and `on_checksum_mismatch="raise"`.
        """
        event_key: _EventKey = (
            (
                entry.event.latitude,
                entry.event.longitude,
                entry.event.depth,
                entry.event.time,
            )
            if entry.event is not None
            else None
        )
        key: _CacheKey = (
            entry.station.network,
            entry.station.name,
            entry.station.location,
            entry.station.channel,
            event_key,
            entry.starttime,
            entry.endtime,
        )
        with self._lock:
            cached = self._cache.get(key)
            generation = self._cache_generation
        if cached is None:
            # Deliberately outside the lock — see the class docstring's
            # thread-safety note: two threads racing the same not-yet-cached
            # key both fetch here (a stampede) before one result wins.
            starttime, endtime, predicted = self._resolve_window(entry)
            seismogram = self.fetch_seismogram(entry.station, starttime, endtime)
            checksum = _checksum(seismogram)
            context = FetchContext(
                entry=entry,
                starttime=starttime,
                endtime=endtime,
                predicted=predicted,
            )
            fresh = (checksum, self.seismogram_transform(seismogram, context))
            with self._lock:
                if self._cache_generation == generation:
                    cached = self._cache.setdefault(key, fresh)
                else:
                    # A parameter changed (clearing the cache) while this
                    # fetch was in flight: `key` doesn't encode it, so return
                    # this result once without caching it under a stale key.
                    cached = fresh

        checksum, result = cached
        if entry.checksum is None:
            entry.checksum = checksum
        elif entry.checksum != checksum and self.on_checksum_mismatch != "ignore":
            message = (
                f"Fetched data for {entry.station.network}.{entry.station.name} "
                "no longer matches the checksum recorded when this entry was "
                "first fetched — the underlying archive may have been revised."
            )
            if self.on_checksum_mismatch == "raise":
                raise ValueError(message)
            # `_stacklevel` is threaded in from the public entry point
            # (`seismogram`/`fetch_all` pass the default; `seismograms_for`
            # passes one level deeper) so the warning always points at the
            # user's own call site, not an intermediate method.
            warnings.warn(message, stacklevel=_stacklevel)
        return result

    @property
    def stations(self) -> list[TStation]:
        """Distinct stations across all entries, in first-seen order.

        A plain `@property`, not `@cached_property` — recomputed on each
        access, same as
        [`ICCS.cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]'s
        precedent for a no-arg derived list view in this codebase. Compares
        with `==` (attrs-generated equality, not identity or hashing —
        `Station` is not hashable).
        """
        seen: list[TStation] = []
        for entry in self.entries:
            if entry.station not in seen:
                seen.append(entry.station)
        return seen

    @property
    def events(self) -> list[TEvent]:
        """Distinct events across all entries, excluding event-less entries.

        In first-seen order; compares with `==`, same caveat as `stations`.
        """
        seen: list[TEvent] = []
        for entry in self.entries:
            if entry.event is not None and entry.event not in seen:
                seen.append(entry.event)
        return seen

    def events_for(self, station: TStation) -> list[TEvent | None]:
        """Events available for one station, in first-seen order.

        `None` appears in the result if `station` has an event-less entry —
        an event-less selection is a first-class member of this list, not a
        special case to check for separately.
        """
        seen: list[TEvent | None] = []
        for entry in self.entries:
            if entry.station == station and entry.event not in seen:
                seen.append(entry.event)
        return seen

    def stations_for(self, event: TEvent | None) -> list[TStation]:
        """Stations available for one event, in first-seen order.

        Pass `None` for stations with an event-less entry.
        """
        seen: list[TStation] = []
        for entry in self.entries:
            if entry.event == event and entry.station not in seen:
                seen.append(entry.station)
        return seen

    def seismogram(
        self,
        station: TStation,
        event: TEvent | None = None,
        *,
        _stacklevel: int = 3,
    ) -> TSeismogram:
        """Fetch (or return from cache) the result for one station/event combination.

        Args:
            station: Station to fetch.
            event: Event to fetch for, or `None` for an event-less entry.

        Returns:
            The transformed result for the matching entry.

        Raises:
            KeyError: If no entry matches this station/event combination.
            ValueError: If more than one entry matches — an authoring
                mistake (e.g. the same station/event added twice with
                different explicit windows), surfaced rather than silently
                resolved by picking one.
        """
        matches = [e for e in self.entries if e.station == station and e.event == event]
        if not matches:
            raise KeyError("No entry for this station/event combination.")
        if len(matches) > 1:
            raise ValueError(
                "More than one entry matches this station/event combination."
            )
        return self._fetch(matches[0], _stacklevel=_stacklevel)

    def seismograms_for(self, event: TEvent) -> list[TSeismogram]:
        """All seismograms for one event — e.g. ready for `ICCS(seismograms=...)`.

        Built from
        [`stations_for`][pysmo.tools.project.PysmoProject.stations_for] and
        [`seismogram`][pysmo.tools.project.PysmoProject.seismogram], not an
        independent filter over `entries`.

        Typed to require an `Event`, unlike `stations_for`/`events_for`
        (which both treat `None` as first-class) — deliberately: this
        method exists for the event-based bulk-fetch use case (`ICCS`),
        which has no equivalent "all event-less entries" workflow to
        support. `[seismogram(s, None) for s in stations_for(None)]`
        already covers that case directly if it's ever needed.
        """
        return [
            self.seismogram(station, event, _stacklevel=4)
            for station in self.stations_for(event)
        ]

    def fetch_all(self) -> list[TSeismogram]:
        """Fetch every entry in the project.

        With the default, always-fresh `fetch_seismogram`, this just warms
        `_cache` for the session. With an archive-backed `fetch_seismogram`
        (e.g.
        [`SqliteArchiveFetcher`][pysmo.tools.archive.SqliteArchiveFetcher]),
        this is what actually populates the archive — a single, explicit
        "get everything this project needs into the archive" call, rather
        than relying on incidental use of `seismogram`/`seismograms_for` to
        cover every entry eventually.

        Returns:
            One transformed result per entry, in `entries` order.
        """
        return [self._fetch(entry) for entry in self.entries]
