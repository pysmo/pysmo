"""The PysmoProject class and functions used within the class."""

from __future__ import annotations

import threading
import warnings
from typing import Any, ClassVar, Literal

import pandas as pd
from attrs import Attribute, define, field, setters, validators

from pysmo import Event, MiniSeismogram, Seismogram, Station, __version__
from pysmo._utils import attrs_getstate, attrs_setstate
from pysmo.classes import MSeed
from pysmo.functions import clone_to_mini, seismogram_checksum

from ._entry import ProjectEntry
from ._identity import UnknownEntryIdentity, entry_identity, resolution_context_digest
from ._phasewindow import PhaseWindow
from ._types import (
    FetchContext,
    SeismogramFetcher,
    SeismogramTransform,
    WindowResolver,
    WindowResult,
)

__all__ = ["FetchContext", "PysmoProject"]


def _default_fetch_seismogram(
    station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> Seismogram:
    """Default `fetch_seismogram` implementation for `PysmoProject`.

    Fetches and parses a waveform from the EarthScope FDSN dataselect
    service as miniSEED, via [`MSeed.fetch`][pysmo.classes.MSeed.fetch].
    """
    return MSeed.fetch(station=station, starttime=starttime, endtime=endtime)


def _seismogram_to_mini_seismogram[TStation: Station, TEvent: Event](
    seismogram: Seismogram, context: FetchContext[TStation, TEvent]
) -> MiniSeismogram:
    """Default `seismogram_transform`: the raw downloaded trace as a `MiniSeismogram`.

    No processing: response removal, detrending and the like stay an
    explicit opt-in via a custom `seismogram_transform`.
    """
    return clone_to_mini(MiniSeismogram, seismogram)


def _on_setattr_clear_cache[T](
    instance: PysmoProject[Any, Any, Any], attribute: Attribute[T], value: T
) -> T:
    """Setter that clears the fetch cache when a parameter affecting it changes."""
    if (current := getattr(instance, attribute.name)) is value:
        return value
    if (current == value) is True:
        return value
    instance.clear_cache()
    return value


type _CacheKey = str
"""An [`entry.identity`][pysmo.tools.project.ProjectEntry.identity] string:
the entry's content fingerprint (station codes, event hypocentre, explicit
window). A `WindowResolver` is a pure function of the entry, so two entries
with the same identity resolve to the same window; keying on identity is
strategy-agnostic (it encodes nothing about what a resolver reads) yet keeps
distinct events apart, which a resolved-window key does not for two explicit
windows that happen to coincide."""


@define(kw_only=True)
class PysmoProject[TStation: Station, TEvent: Event, TSeismogram = MiniSeismogram]:
    """Declares station/event data to fetch on demand and transform into `TSeismogram`.

    A `PysmoProject` holds a flat list of
    [`ProjectEntry`][pysmo.tools.project.ProjectEntry] objects plus three
    pluggable callables: `window` resolves each entry's fetch window,
    `fetch_seismogram` downloads the trace, and `seismogram_transform` turns
    it into the caller's target type `TSeismogram`. No waveform data are
    stored on the instance between calls beyond an in-memory cache of
    already-fetched-and-transformed results.

    An optional `name` can label the project for identification by tools
    that hold more than one project. It is free-text and carries no
    semantics: it is not a key, does not affect cache invalidation, and is
    not part of `resolution_context_digest` or any entry identity.

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

    Note: Persistence
        A `PysmoProject` travels as a pickle. The in-memory cache and lock
        are dropped during pickling and reconstructed on unpickling. An
        optional `name` is preserved across pickles; unpickling a project
        serialised without a `name` defaults it to `None`.

    Note: Thread-safety
        The in-memory fetch cache is safe to touch from multiple threads
        calling [`seismogram`][pysmo.tools.project.PysmoProject.seismogram],
        [`seismograms_for`][pysmo.tools.project.PysmoProject.seismograms_for],
        or [`fetch_all`][pysmo.tools.project.PysmoProject.fetch_all] on the
        same instance concurrently. This does not parallelise fetching
        itself, though: `fetch_seismogram` is called outside the lock, so
        two threads racing the same not-yet-cached entry both still fetch
        before one result wins and is cached.

        Reassigning `window` (or any other cache-affecting field) on one
        thread while another is mid-fetch is also safe: the in-flight fetch
        still returns a result, it just isn't cached (the next call
        recomputes it with the current parameters).
    """

    _FORMAT_VERSION: ClassVar[int] = 2

    name: str | None = field(
        default=None,
        validator=validators.optional(validators.instance_of(str)),
    )
    """Optional free-text label for this project.

    Useful for identification by downstream tools that hold multiple
    projects. This is purely a label, not a key: no uniqueness is enforced,
    renaming does not invalidate the fetch cache, and it is not part of
    [`resolution_context_digest`][pysmo.tools.project.PysmoProject.resolution_context_digest]
    or any entry identity.
    """

    entries: list[ProjectEntry[TStation, TEvent]] = field(
        factory=list, on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache)
    )
    """Station/event/window selections making up this project.

    Build them with
    [`build_entries`][pysmo.tools.project.build_entries]; grow the project
    later with `project.entries.extend(build_entries(...))` (a plain
    in-place mutation; call
    [`clear_cache`][pysmo.tools.project.PysmoProject.clear_cache] afterwards
    only to free memory, never for correctness, since the fetch cache is
    keyed by entry content).
    """

    seismogram_transform: SeismogramTransform[TStation, TEvent, TSeismogram] = field(
        # The default returns `MiniSeismogram`, which is `TSeismogram`'s own
        # default, but mypy still can't match a concrete return against the
        # bare type parameter in the class body.
        default=_seismogram_to_mini_seismogram,  # type: ignore[assignment]
        on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache),
    )
    """Convert a freshly downloaded seismogram into the target type `TSeismogram`.

    Any [`SeismogramTransform`][pysmo.tools.project.SeismogramTransform] (see
    there for the call contract). Defaults to returning the raw trace as a
    [`MiniSeismogram`][pysmo.MiniSeismogram], with no processing: a custom
    transform is where response removal, detrending and resampling belong,
    and it may issue its own additional fetches, as the
    [module documentation][pysmo.tools.project]'s example does for instrument
    response metadata. A callable `attrs` class with only picklable fields is
    the way to give the transform its own configuration.
    """

    fetch_seismogram: SeismogramFetcher = field(
        default=_default_fetch_seismogram,
        on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache),
    )
    """Download a seismogram for a station and absolute time window.

    Any [`SeismogramFetcher`][pysmo.tools.project.SeismogramFetcher] (see
    there for the call contract). Defaults to a private helper wrapping
    [`MSeed.fetch`][pysmo.classes.MSeed.fetch], the explicit "always fresh,
    never cached" choice.

    For any project where reproducibility matters, substitute a
    [`FetchCache`][pysmo.tools.cache.FetchCache] instance instead. That is
    the *recommended* value for real analysis work, not a power-user option
    on equal footing with the default; see its own docstring for why, and
    how it differs from `ProjectEntry.checksum`'s live-fetch drift
    detection. Leave its `max_bytes` at the default
    (unlimited) for this to hold: a finite `max_bytes` evicts old entries and
    re-fetches them on next access, reintroducing the drift a cache is meant
    to rule out. It only pins the waveform, though: see the
    [module documentation][pysmo.tools.project]'s second example for the
    gotcha it does not cover, `seismogram_transform` making its own
    additional fetches.
    """

    window: WindowResolver[TStation, TEvent] = field(
        default=PhaseWindow(),
        on_setattr=setters.pipe(setters.convert, _on_setattr_clear_cache),
    )
    """Resolve an entry's fetch window when it carries no explicit one.

    Any [`WindowResolver`][pysmo.tools.project.WindowResolver] (see there for
    the call contract). Defaults to
    [`PhaseWindow`][pysmo.tools.project.PhaseWindow], which places the window
    around a predicted phase arrival. An entry with an explicit
    `starttime`/`endtime` bypasses this entirely, so a custom resolver only
    ever handles the event-derived case.
    """

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
    value from the *first* fetch; it is never overwritten by a mismatching
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
    than one thread (see the class docstring's thread-safety note)."""

    def __getstate__(self) -> dict[str, Any]:
        """Drop the fetch cache and lock, neither of which can survive pickling."""
        state = attrs_getstate(self, {"_cache": {}, "_cache_generation": 0})
        del state["_lock"]
        state["_format_version"] = self._FORMAT_VERSION
        state["_pysmo_version"] = __version__
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore state without firing `on_setattr` hooks, then make a fresh lock."""
        pickled_format = state.pop("_format_version", 0)
        pickled_pysmo = state.pop("_pysmo_version", "unknown")
        if pickled_format != self._FORMAT_VERSION:
            raise ValueError(
                f"This PysmoProject was pickled by pysmo {pickled_pysmo} in state "
                + f"format v{pickled_format}; this pysmo ({__version__}) uses "
                + f"v{self._FORMAT_VERSION}. Re-create the project."
            )
        state.setdefault("name", None)
        attrs_setstate(self, state)
        object.__setattr__(self, "_lock", threading.Lock())

    def clear_cache(self) -> None:
        """Clear the in-memory fetch cache.

        Cleared automatically whenever
        [`entries`][pysmo.tools.project.PysmoProject.entries],
        [`window`][pysmo.tools.project.PysmoProject.window],
        [`seismogram_transform`][pysmo.tools.project.PysmoProject.seismogram_transform],
        or
        [`fetch_seismogram`][pysmo.tools.project.PysmoProject.fetch_seismogram]
        is *reassigned*.

        Call this manually after any in-place mutation of
        [`entries`][pysmo.tools.project.PysmoProject.entries] (e.g. `append`,
        `remove`, or index assignment), which isn't observable by
        `on_setattr` and therefore doesn't clear the cache automatically.
        """
        with self._lock:
            self._cache.clear()
            self._cache_generation += 1

    def _fetch(
        self, entry: ProjectEntry[TStation, TEvent], *, _stacklevel: int = 3
    ) -> TSeismogram:
        """Fetch, transform, and cache the seismogram for one entry.

        Internal primitive; see
        [`seismogram`][pysmo.tools.project.PysmoProject.seismogram] for the
        public, station/event-based accessor built on top of this.

        Args:
            entry: The station/event/window selection to fetch.

        Returns:
            The transformed result for `entry`, from cache if an entry with
            the same [`identity`][pysmo.tools.project.ProjectEntry.identity]
            has been fetched before.

        Raises:
            ValueError: If `window` cannot resolve a window for `entry`; if
                the underlying fetch raises (e.g. no waveform data for the
                resolved window); or if the checksum no longer matches and
                `on_checksum_mismatch="raise"`.
        """
        key: _CacheKey = entry_identity(entry)
        with self._lock:
            cached = self._cache.get(key)
            generation = self._cache_generation
        if cached is None:
            # Resolve the window only on a miss: an explicit window on the
            # entry wins (it is entry data, not resolution policy), else the
            # `window` resolver derives one. Resolution and the fetch both
            # run outside the lock (see the class docstring's thread-safety
            # note): a concurrent `self.window` reassignment is a tolerated
            # torn read, `generation` (read above) guards the write-back, and
            # two threads racing the same key both fetch before one wins.
            if entry.starttime is not None and entry.endtime is not None:
                window = WindowResult(
                    starttime=entry.starttime, endtime=entry.endtime, reference=None
                )
            else:
                window = self.window(entry)
            seismogram = self.fetch_seismogram(
                entry.station, window.starttime, window.endtime
            )
            # Checksum the raw trace pre-transform: the transform's output can
            # be mutated by downstream consumers (`ICCS` edits `t0`/`t1`/`flip`
            # during a run), which would otherwise read back as false drift.
            checksum = seismogram_checksum(seismogram)
            context = FetchContext(
                entry=entry,
                starttime=window.starttime,
                endtime=window.endtime,
                reference=window.reference,
            )
            fresh = (checksum, self.seismogram_transform(seismogram, context))
            with self._lock:
                if self._cache_generation == generation:
                    cached = self._cache.setdefault(key, fresh)
                else:
                    # A parameter changed (clearing the cache) while this
                    # fetch was in flight: return this result once without
                    # caching it under a now-stale key.
                    cached = fresh

        checksum, result = cached
        with self._lock:
            recorded = entry.checksum
            if recorded is None:
                entry.checksum = checksum
        if (
            recorded is not None
            and recorded != checksum
            and (self.on_checksum_mismatch != "ignore")
        ):
            message = (
                f"Fetched data for {entry.station.network}.{entry.station.name} "
                + "no longer matches the checksum recorded when this entry was "
                + "first fetched: the cache was revised, or fetch_seismogram "
                + "now yields the same samples in a different dtype."
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

        A plain `@property`, not `@cached_property`: recomputed on each
        access, same as
        [`ICCS.cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]'s
        precedent for a no-arg derived list view in this codebase. Compares
        with `==` (attrs-generated equality, not identity or hashing;
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

    @property
    def resolution_context_digest(self) -> str:
        """Digest over the project parameters that determine fetched content.

        Covers `window` and `seismogram_transform`. Reassigning
        `fetch_seismogram` (e.g. to an on-disk fetch cache) leaves the
        digest unchanged.

        Examples:
            >>> from pysmo.tools.project import PysmoProject
            >>> project = PysmoProject()
            >>> project.resolution_context_digest.startswith("rc2:")
            True
            >>> len(project.resolution_context_digest)
            68
        """
        return resolution_context_digest(self)

    def events_for(self, station: TStation) -> list[TEvent | None]:
        """Events available for one station, in first-seen order.

        `None` appears in the result if `station` has an event-less entry; an
        event-less selection is a first-class member of this list, not a
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
            ValueError: If more than one entry matches: an authoring
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

    def get(self, identity: str, *, _stacklevel: int = 3) -> TSeismogram:
        """Fetch (or return from cache) the result for an entry by its identity.

        Args:
            identity: An [`entry.identity`][pysmo.tools.project.ProjectEntry.identity]
                string. The entry need not have been fetched before.

        Returns:
            The transformed result for the matching entry.

        Raises:
            UnknownEntryIdentity: If no entry matches this identity.
            ValueError: If more than one entry matches: an authoring mistake,
                surfaced rather than silently resolved by picking one.

        Examples:
            >>> import pandas as pd
            >>> from pysmo import MiniEvent, MiniSeismogram, MiniStation, Station
            >>> from pysmo.tools.project import ProjectEntry, PysmoProject
            >>> def fake_fetch(station: Station, t0: pd.Timestamp, t1: pd.Timestamp):
            ...     return MiniSeismogram(
            ...         begin_time=t0, delta=pd.Timedelta(seconds=1), data=[1.0, 2.0]
            ...     )
            >>> station = MiniStation(
            ...     name="ANMO",
            ...     network="IU",
            ...     location="00",
            ...     channel="BHZ",
            ...     latitude=34.9459,
            ...     longitude=-106.4571,
            ... )
            >>> entry = ProjectEntry(
            ...     station=station,
            ...     starttime=pd.Timestamp("2020-01-01T00:00:00Z"),
            ...     endtime=pd.Timestamp("2020-01-01T00:10:00Z"),
            ... )
            >>> project = PysmoProject(entries=[entry], fetch_seismogram=fake_fetch)
            >>> seis = project.get(entry.identity)
            >>> len(seis.data)
            2
        """
        matches = [e for e in self.entries if entry_identity(e) == identity]
        if not matches:
            raise UnknownEntryIdentity(identity)
        if len(matches) > 1:
            raise ValueError(f"More than one entry resolves to identity {identity!r}.")
        return self._fetch(matches[0], _stacklevel=_stacklevel)

    def seismograms_for(self, event: TEvent) -> list[TSeismogram]:
        """All seismograms for one event, e.g. ready for `ICCS(seismograms=...)`.

        Built from
        [`stations_for`][pysmo.tools.project.PysmoProject.stations_for] and
        [`seismogram`][pysmo.tools.project.PysmoProject.seismogram], not an
        independent filter over `entries`.

        Typed to require an `Event`, unlike `stations_for`/`events_for`
        (which both treat `None` as first-class), deliberately: this
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
        `_cache` for the session. With a cache-backed `fetch_seismogram`
        (e.g. [`FetchCache`][pysmo.tools.cache.FetchCache]), this is what
        actually populates the on-disk cache: a single, explicit "get
        everything this project needs onto disk" call, rather
        than relying on incidental use of `seismogram`/`seismograms_for` to
        cover every entry eventually.

        Returns:
            One transformed result per entry, in `entries` order.
        """
        return [self._fetch(entry) for entry in self.entries]
