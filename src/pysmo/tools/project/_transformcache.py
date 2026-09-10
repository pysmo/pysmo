"""On-disk cache for the output of a `PysmoProject`'s `seismogram_transform`."""

import json
from pathlib import Path
from typing import Any, cast

from attrs import define, field, validators

from pysmo import Event, Seismogram, Station
from pysmo._utils import attrs_getstate, attrs_setstate
from pysmo.functions import (
    seismogram_checksum,
    seismogram_from_json,
    seismogram_to_json,
)
from pysmo.functions._serialize import _SEISMOGRAM_JSON_VERSION
from pysmo.lib.converters import to_utc_timestamp
from pysmo.tools.cache import BlobCache
from pysmo.typing import PositiveInt

from ._identity import callable_identity
from ._types import FetchContext, SeismogramTransform

__all__ = ["TransformCache"]

_ENCODING_VERSION = 1000 + _SEISMOGRAM_JSON_VERSION
"""`BlobCache` layout version for a transform-cache file. Offset from
`cache._FETCH_ENCODING_VERSION`'s range so a raw-fetch cache and a
JSON-document cache cannot be opened on each other's files."""


@define(kw_only=True)
class TransformCache[TStation: Station, TEvent: Event, TSeismogram]:
    """Caches a `seismogram_transform`'s output, and its secondary fetches, on disk.

    A [`SeismogramTransform`][pysmo.tools.project.SeismogramTransform] for
    [`PysmoProject`][pysmo.tools.project.PysmoProject] that wraps another
    transform. On a miss it runs the wrapped transform and stores its result
    as a [`seismogram_to_json`][pysmo.functions.seismogram_to_json] document
    in a [`BlobCache`][pysmo.tools.cache.BlobCache]; on a hit it reconstructs
    the result from JSON without running the transform at all, which also
    skips whatever additional fetches (instrument response metadata, say) the
    transform issues on its own. That second effect is usually the reason to
    reach for this: a [`FetchCache`][pysmo.tools.cache.FetchCache] pins the
    waveform but says nothing about a transform's own network calls.

    The cache key folds in every part of the fetch the wrapped transform can
    observe: the entry's identity, the resolved window and its reference
    time, the wrapped transform's configuration
    ([`callable_identity`][pysmo.tools.project.callable_identity]), and a
    [`seismogram_checksum`][pysmo.functions.seismogram_checksum] of the
    transform's input seismogram. A change to any of them mints a new key with
    no explicit purge; an evicted or drifted input drains naturally. Every
    call hashes the input seismogram to build the key, a hit included.

    Only value-object `attrs` seismograms round-trip:
    [`MiniSeismogram`][pysmo.MiniSeismogram],
    [`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram],
    [`GeoCsvSeismogram`][pysmo.classes.GeoCsvSeismogram], and any user type
    whose fields are primitives, collections, nested `attrs`, or the three
    leaf types the codec handles. A transform returning anything else (a
    `SacSeismogram` live view, a type with an unhookable field) raises
    `TypeError` at store time, naming
    [`clone_to_mini`][pysmo.functions.clone_to_mini].

    Examples:
        ```python
        >>> import pandas as pd
        >>> from pathlib import Path
        >>> import tempfile
        >>> from pysmo import MiniEvent, MiniSeismogram, MiniStation, Seismogram
        >>> from pysmo.functions import clone_to_mini
        >>> from pysmo.tools.project import FetchContext, ProjectEntry
        >>> from pysmo.tools.project import TransformCache
        >>>
        >>> calls = []
        >>> def double(seismogram: Seismogram, context: FetchContext) -> MiniSeismogram:
        ...     calls.append(1)
        ...     return clone_to_mini(MiniSeismogram, seismogram)
        ...
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="BHZ",
        ...     latitude=34.9, longitude=-106.5,
        ... )
        >>> event = MiniEvent(
        ...     latitude=-36.1, longitude=-72.9, depth=22900.0,
        ...     time=pd.Timestamp("2010-02-27T06:34:11Z"),
        ... )
        >>> entry = ProjectEntry(station=station, event=event)
        >>> context = FetchContext(
        ...     entry=entry,
        ...     starttime=pd.Timestamp("2010-02-27T06:40:00Z"),
        ...     endtime=pd.Timestamp("2010-02-27T06:50:00Z"),
        ...     reference=pd.Timestamp("2010-02-27T06:44:00Z"),
        ... )
        >>> raw = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:40:00Z"),
        ...     delta=pd.Timedelta(seconds=1), data=[1.0, 2.0, 3.0],
        ... )
        >>>
        >>> cache = TransformCache(
        ...     path=Path(tempfile.mkdtemp()) / "transform.sqlite3", transform=double
        ... )
        >>> first = cache(raw, context)   # miss: runs the wrapped transform
        >>> second = cache(raw, context)  # hit: reconstructed from JSON
        >>> len(calls)
        1
        >>> second.data.tolist()
        [1.0, 2.0, 3.0]
        >>>
        ```
    """

    path: Path = field(converter=Path, metadata={"identity": False})
    """Location of the SQLite database file.

    The file itself is created on first use; its *parent directory* must
    already exist, checked at construction time. Not part of the wrapper's
    [`callable_identity`][pysmo.tools.project.callable_identity]: moving the
    cache file does not change what a call returns.
    """

    transform: SeismogramTransform[TStation, TEvent, TSeismogram]
    """The wrapped transform, run only on a cache miss.

    Must be picklable by reference (a top-level function or a callable
    `attrs` instance), the same constraint `PysmoProject` places on
    `seismogram_transform` itself.
    """

    wal: bool = field(default=False, metadata={"identity": False})
    """Enable WAL mode (local disk only; see
    [`BlobCache`][pysmo.tools.cache.BlobCache])."""

    max_bytes: PositiveInt | None = field(
        default=None,
        validator=validators.optional(validators.gt(0)),
        metadata={"identity": False},
    )
    """Maximum total size of compressed data stored, in bytes; `None` for
    unlimited. See [`BlobCache.max_bytes`][pysmo.tools.cache.BlobCache]."""

    verify: bool = True
    """Re-decode each freshly stored result and compare it to the transform's
    output, raising `TypeError` on any mismatch.

    Catches a codec that silently loses information on a rich `TSeismogram`
    (e.g. a non-primitive value in `MiniIccsSeismogram.extra`). Leave on
    unless the transform output is known to be a plain
    [`MiniSeismogram`][pysmo.MiniSeismogram]."""

    trusted_modules: tuple[str, ...] = field(
        default=("pysmo",), metadata={"identity": False}
    )
    """Top-level packages a cached result's type may be imported from when it
    is rebuilt on a hit. The pysmo value objects
    ([`MiniSeismogram`][pysmo.MiniSeismogram] and friends) are covered by the
    default; widen it only if the wrapped transform returns a value object
    defined in your own package."""

    _cache: BlobCache = field(init=False, repr=False, eq=False)

    def __attrs_post_init__(self) -> None:
        """Build the inner store (which also checks `path`'s parent exists)."""
        self._cache = self._build_cache()

    def _build_cache(self) -> BlobCache:
        return BlobCache(
            path=self.path,
            encoding_version=_ENCODING_VERSION,
            wal=self.wal,
            max_bytes=self.max_bytes,
        )

    def __getstate__(self) -> dict[str, Any]:
        """Drop the inner store; it is rebuilt from the plain fields on unpickling."""
        state = attrs_getstate(self, {})
        del state["_cache"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore the plain fields, then rebuild the inner store."""
        attrs_setstate(self, state)
        self._cache = self._build_cache()

    def close(self) -> None:
        """Close the inner store's connection, if one is open."""
        self._cache.close()

    def __call__(
        self, seismogram: Seismogram, context: FetchContext[TStation, TEvent]
    ) -> TSeismogram:
        """Return the transformed result for this fetch, from cache when possible.

        Args:
            seismogram: The freshly fetched trace, the wrapped transform's input.
            context: The originating entry and this fetch's resolved window.

        Returns:
            The wrapped transform's result: reconstructed from JSON on a hit,
            freshly computed (and then stored) on a miss.
        """
        key = json.dumps(
            [
                context.entry.identity,
                to_utc_timestamp(context.starttime).isoformat(),
                to_utc_timestamp(context.endtime).isoformat(),
                None
                if context.reference is None
                else to_utc_timestamp(context.reference).isoformat(),
                callable_identity(self.transform),
                seismogram_checksum(seismogram),
            ]
        )

        def produce() -> bytes:
            # `TSeismogram` is unbounded; `seismogram_to_json` gates the type
            # at runtime and raises `TypeError` for anything it cannot encode.
            result = cast(Seismogram, self.transform(seismogram, context))
            return seismogram_to_json(result, verify=self.verify)

        blob = self._cache.get(key, produce)
        return cast(
            TSeismogram,
            seismogram_from_json(blob, trusted_modules=self.trusted_modules),
        )
