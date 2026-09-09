"""On-disk waveform caching: fetch a station and window once, replay it later.

[`FetchCache`][pysmo.tools.cache.FetchCache] is the main entry point. Built
from a fetch function and a parser, it behaves as a callable
`(station, starttime, endtime) -> Seismogram`. The first call for a given
station and window downloads and stores the raw response; later calls for
the same station and window read it back from the file, with no network
access. Its call signature is
[`SeismogramFetcher`][pysmo.tools.project.SeismogramFetcher], so it can also
be a [`PysmoProject`][pysmo.tools.project.PysmoProject]'s `fetch_seismogram`.

[`BlobCache`][pysmo.tools.cache.BlobCache] is the storage layer underneath:
a keyed store of byte blobs in a single SQLite file, compressed, with an
optional size cap. `FetchCache` uses it for raw fetch responses;
[`TransformCache`][pysmo.tools.project.TransformCache] uses it for
transformed seismograms. Use it directly to cache anything else that is
costly to produce and reduces to bytes.

Tip: Portable on disk
    A cache file is an ordinary SQLite database: one table, each row a
    zlib-compressed entry. A SQLite client and zlib are all it takes to read
    the contents back, in any language.

Examples:
    Fetch a window of SAC data once, then replay it from disk on the next
    run. [`FetchCache`][pysmo.tools.cache.FetchCache] is paired here with
    [`fetch_sac`][pysmo.tools.web.fetch_sac] and
    [`SAC.from_zip`][pysmo.classes.SAC.from_zip].

    <!-- skip: start if(not run_real_web_requests) -->
    ```python
    >>> import pandas as pd
    >>> from pysmo import MiniStation, Seismogram
    >>> from pysmo.classes import SAC
    >>> from pysmo.tools.cache import FetchCache
    >>> from pysmo.tools.web import fetch_sac
    >>>
    >>> def parse_sac_seismogram_zip(raw: bytes) -> Seismogram:
    ...     return SAC.from_zip(raw).seismogram
    ...
    >>> station = MiniStation(
    ...     name="ANMO", network="IU", location="00", channel="LHZ",
    ...     latitude=34.945981, longitude=-106.457133,
    ... )
    >>> starttime = pd.Timestamp("2010-02-27T06:44:00Z")
    >>> endtime = pd.Timestamp("2010-02-27T06:54:00Z")
    >>>
    >>> cache = FetchCache(
    ...     path="waveform_cache.sqlite3", fetch_raw=fetch_sac, parse=parse_sac_seismogram_zip
    ... )
    >>> seismogram = cache(station, starttime, endtime)  # miss: fetches and stores
    >>> seismogram_again = cache(station, starttime, endtime)  # hit: no fetch
    >>> seismogram_again.data.shape == seismogram.data.shape
    True
    >>>
    ```
    <!-- skip: end -->
"""

import json
import sqlite3
import threading
import zlib
from collections.abc import Callable
from itertools import batched
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
from attrs import define, field, validators

from pysmo import Seismogram, Station
from pysmo._utils import attrs_getstate, attrs_setstate
from pysmo.lib.validators import convert_to_utc_timestamp
from pysmo.typing import PositiveInt

__all__ = ["BlobCache", "FetchCache", "RawFetcher", "RawParser"]

_FETCH_ENCODING_VERSION = 1
"""`BlobCache` layout version for a `FetchCache` file; bump on any change to
what the stored bytes mean."""

_LOW_WATER_FRACTION = 0.75
"""On eviction, entries are removed until the total is back down to this
fraction of `max_bytes`. The slack keeps eviction from running on every
subsequent miss."""

_CREATE_CACHE_TABLE = (
    "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, data BLOB NOT NULL)"
)
_CREATE_CACHE_STATS_TABLE = (
    "CREATE TABLE IF NOT EXISTS cache_stats "
    + "(id INTEGER PRIMARY KEY CHECK (id = 1), total_bytes INTEGER NOT NULL)"
)
_CREATE_CACHE_INSERT_TRIGGER = (
    "CREATE TRIGGER IF NOT EXISTS cache_insert_bytes "
    + "AFTER INSERT ON cache "
    + "BEGIN "
    + "  UPDATE cache_stats "
    + "  SET total_bytes = total_bytes + length(NEW.data) "
    + "  WHERE id = 1; "
    + "END"
)
_CREATE_CACHE_DELETE_TRIGGER = (
    "CREATE TRIGGER IF NOT EXISTS cache_delete_bytes "
    + "AFTER DELETE ON cache "
    + "BEGIN "
    + "  UPDATE cache_stats "
    + "  SET total_bytes = MAX(total_bytes - length(OLD.data), 0) "
    + "  WHERE id = 1; "
    + "END"
)
# Schema DDL, defined once here and imported by the tests.


class RawFetcher(Protocol):
    """A callable that returns the raw bytes for a station and time window.

    Called with keyword arguments only, matching pysmo's fetch functions
    ([`fetch_sac`][pysmo.tools.web.fetch_sac],
    [`fetch_mseed`][pysmo.tools.web.fetch_mseed],
    [`fetch_geocsvseismogram`][pysmo.tools.web.fetch_geocsvseismogram]),
    which can be passed straight in as `FetchCache.fetch_raw`.
    """

    def __call__(
        self, *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> bytes:
        """Fetch raw bytes for `station` over `starttime` to `endtime`."""
        ...


type RawParser = Callable[[bytes], Seismogram]
"""A callable that parses raw fetch bytes into a [`Seismogram`][pysmo.Seismogram].

For example [`SAC.from_zip`][pysmo.classes.SAC.from_zip] or
[`MSeed.from_bytes`][pysmo.classes.MSeed.from_bytes]. Must match the format
the [`RawFetcher`][pysmo.tools.cache.RawFetcher] it is paired with returns.
"""


@define(kw_only=True)
class BlobCache:
    """A keyed store of byte blobs in a single SQLite file.

    [`get`][pysmo.tools.cache.BlobCache.get] takes a string key and a
    callback. On a hit it returns the stored blob; on a miss it calls the
    callback, stores what it returns (compressed), and returns that. Keys and
    values are arbitrary bytes; the cache interprets neither.

    Pass `max_bytes` to cap the total stored size; once it is exceeded the
    oldest entries are removed until the cache fits again.

    Warning: Local disk only
        The SQLite file must be on local disk and used by one process at a
        time. WAL mode and concurrent access over a network filesystem are
        unsupported and can corrupt the file.

    Examples:
        ```python
        >>> from pathlib import Path
        >>> import tempfile
        >>> from pysmo.tools.cache import BlobCache
        >>>
        >>> tmp = Path(tempfile.mkdtemp())
        >>> cache = BlobCache(path=tmp / "blobs.sqlite3", encoding_version=1)
        >>> calls = []
        >>> def produce() -> bytes:
        ...     calls.append(1)
        ...     return b"payload"
        ...
        >>> cache.get("some-key", produce)
        b'payload'
        >>> cache.get("some-key", produce)  # hit: produce not called again
        b'payload'
        >>> len(calls)
        1
        >>>
        ```
    """

    path: Path = field(converter=Path)
    """Path to the SQLite file.

    Created on first use; its parent directory must already exist.
    """

    encoding_version: PositiveInt
    """Layout version for the file, recorded on creation and checked on open.

    Opening a file that was written with a different value raises
    `ValueError`. Each cache built on `BlobCache` passes its own constant.
    """

    wal: bool = False
    """Enable SQLite WAL mode (local disk only)."""

    max_bytes: PositiveInt | None = field(
        default=None,
        validator=validators.optional(validators.gt(0)),
    )
    """Cap on the total compressed size of stored blobs, in bytes.

    When a new entry pushes the total past the cap, the oldest entries are
    removed until it fits again. A single entry larger than the cap is stored
    and kept anyway, so it is never re-produced on every call. `None` (the
    default) means no cap. The file on disk is somewhat larger than
    `max_bytes` because of SQLite's own page and index overhead.
    """

    _conn: sqlite3.Connection | None = field(
        init=False, default=None, repr=False, eq=False
    )
    _lock: threading.Lock = field(
        init=False, factory=threading.Lock, repr=False, eq=False
    )
    """Serialises connection setup and writes; the cache may be called from
    more than one thread."""

    def __attrs_post_init__(self) -> None:
        """Fail fast if `path`'s parent directory doesn't exist."""
        if not self.path.parent.is_dir():
            raise FileNotFoundError(
                f"Parent directory does not exist: {self.path.parent}"
            )

    def __getstate__(self) -> dict[str, Any]:
        """Drop the live connection and lock for pickling."""
        state = attrs_getstate(self, {"_conn": None})
        del state["_lock"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore the fields and create a fresh lock."""
        attrs_setstate(self, state)
        object.__setattr__(self, "_lock", threading.Lock())

    def close(self) -> None:
        """Close the database connection.

        Optional: the connection is also closed when the cache is garbage
        collected. Call this to release the handle sooner.
        """
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __del__(self) -> None:
        """Close the connection when the cache is garbage collected."""
        conn = getattr(self, "_conn", None)
        if conn is not None:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
                if self.wal:
                    conn.execute("PRAGMA journal_mode=WAL")
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    conn.execute(f"PRAGMA user_version = {self.encoding_version}")
                elif version != self.encoding_version:
                    conn.close()
                    raise ValueError(
                        f"{self.path} was written with a different cache "
                        + f"encoding (user_version={version}, expected "
                        + f"{self.encoding_version})."
                    )
                conn.execute(_CREATE_CACHE_TABLE)
                conn.execute(_CREATE_CACHE_STATS_TABLE)
                conn.execute(_CREATE_CACHE_INSERT_TRIGGER)
                conn.execute(_CREATE_CACHE_DELETE_TRIGGER)
                row = conn.execute(
                    "SELECT total_bytes FROM cache_stats WHERE id = 1"
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT OR IGNORE INTO cache_stats (id, total_bytes) "
                        + "VALUES (1, (SELECT COALESCE(SUM(length(data)), 0) FROM cache))"
                    )
                self._conn = conn
            return self._conn

    def get(self, key: str, produce: Callable[[], bytes]) -> bytes:
        """Return the blob stored under `key`, producing and storing it on a miss.

        Args:
            key: The cache key.
            produce: Called only on a miss. Must return `bytes`, which are
                stored compressed.

        Returns:
            The blob: read from the file on a hit, from `produce` on a miss.
        """
        conn = self._connect()
        # No lock on the read: `sqlite3` only asks the caller to serialise
        # writes (done in `_store`), and a serialised SQLite build handles
        # concurrent reads on a shared connection itself.
        row = conn.execute("SELECT data FROM cache WHERE key = ?", (key,)).fetchone()
        if row is not None:
            return zlib.decompress(row[0])
        produced = produce()
        self._store(conn, key, zlib.compress(produced))
        return produced

    def _store(self, conn: sqlite3.Connection, key: str, compressed: bytes) -> None:
        with self._lock, conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO cache (key, data) VALUES (?, ?)",
                (key, compressed),
            )
            if cursor.rowcount > 0:
                if cursor.lastrowid is None:
                    raise RuntimeError("newly inserted cache row has no rowid")
                self._evict(conn, cursor.lastrowid)

    def _evict(self, conn: sqlite3.Connection, inserted_rowid: int) -> None:
        max_bytes = self.max_bytes
        if max_bytes is None:
            return
        if self._tracked_total(conn) <= max_bytes:
            return
        real = self._real_total(conn)
        if real <= max_bytes:
            # Tracked total overstated real usage (e.g. an uncounted external
            # delete); heal the counter without evicting anything.
            conn.execute("UPDATE cache_stats SET total_bytes = ? WHERE id = 1", (real,))
            return
        # Truly over limit: evict the oldest entries down to the low-water
        # mark, so a full cache does not re-check ground truth every miss.
        target = int(max_bytes * _LOW_WATER_FRACTION)
        freed = self._delete_oldest(conn, inserted_rowid, real - target)
        conn.execute(
            "UPDATE cache_stats SET total_bytes = ? WHERE id = 1", (real - freed,)
        )

    def _tracked_total(self, conn: sqlite3.Connection) -> int:
        row = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()
        if row is not None and row[0] >= 0:
            return row[0]
        # Rebuild if the cache_stats row is missing or stale. A negative total
        # is never legitimate and means the counter no longer matches which
        # rows the triggers have accounted for.
        real = self._real_total(conn)
        conn.execute(
            "INSERT OR REPLACE INTO cache_stats (id, total_bytes) VALUES (1, ?)",
            (real,),
        )
        return real

    def _real_total(self, conn: sqlite3.Connection) -> int:
        return int(
            conn.execute("SELECT COALESCE(SUM(length(data)), 0) FROM cache").fetchone()[
                0
            ]
        )

    def _delete_oldest(
        self, conn: sqlite3.Connection, inserted_rowid: int, excess: int
    ) -> int:
        cursor_iter = conn.execute(
            "SELECT rowid, length(data) FROM cache "
            + "WHERE rowid != ? "
            + "ORDER BY rowid ASC",
            (inserted_rowid,),
        )
        to_delete: list[int] = []
        freed = 0
        for rowid, length in cursor_iter:
            to_delete.append(rowid)
            freed += length
            if freed >= excess:
                break
        cursor_iter.close()
        for chunk in batched(to_delete, 500):
            placeholders = ",".join("?" * len(chunk))
            conn.execute(f"DELETE FROM cache WHERE rowid IN ({placeholders})", chunk)
        return freed


@define(kw_only=True)
class FetchCache:
    """A waveform cache: fetch a station and window once, re-parse it from a file.

    Call it as `(station, starttime, endtime) -> Seismogram`. On the first
    call for a given station and window it runs `fetch_raw`, stores the raw
    response, and returns `parse` of it; later calls for the same station and
    window read the stored bytes and return `parse` of those, without
    fetching. `parse` therefore runs on every call, and the file holds the
    unparsed response, which any other tool can read. For a project that
    should also skip the transform on a hit, see
    [`TransformCache`][pysmo.tools.project.TransformCache].

    Any format works, as long as `fetch_raw` and `parse` agree (e.g.
    [`fetch_sac`][pysmo.tools.web.fetch_sac] with
    [`SAC.from_zip`][pysmo.classes.SAC.from_zip]). While a window stays
    cached it is replayed byte-for-byte; an entry evicted under a finite
    `max_bytes` is fetched again on next access.

    The call signature is
    [`SeismogramFetcher`][pysmo.tools.project.SeismogramFetcher], so an
    instance also serves as a
    [`PysmoProject`][pysmo.tools.project.PysmoProject]'s `fetch_seismogram`.
    A database written by pysmo's earlier `SqliteArchiveFetcher` is read
    as-is, without migration.
    """

    path: Path = field(converter=Path)
    """Path to the SQLite file.

    Created on first use; its parent directory must already exist.
    """

    fetch_raw: RawFetcher
    """Fetches the raw response for a station and time window."""

    parse: RawParser
    """Parses a raw response into a `Seismogram`. Runs on every call."""

    wal: bool = False
    """Enable SQLite WAL mode (local disk only)."""

    max_bytes: PositiveInt | None = field(
        default=None,
        validator=validators.optional(validators.gt(0)),
    )
    """Cap on the total stored size in bytes; see
    [`BlobCache.max_bytes`][pysmo.tools.cache.BlobCache.max_bytes]. `None`
    (the default) means no cap, so a cached window is never evicted and
    re-fetched.
    """

    _cache: BlobCache = field(init=False, repr=False, eq=False)

    def __attrs_post_init__(self) -> None:
        """Build the inner store (which also checks `path`'s parent exists)."""
        self._cache = self._build_cache()

    def _build_cache(self) -> BlobCache:
        return BlobCache(
            path=self.path,
            encoding_version=_FETCH_ENCODING_VERSION,
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
        self, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> Seismogram:
        """Return the `Seismogram` for `station` and window, from cache when possible.

        Args:
            station: Station to fetch data for.
            starttime: Start of the requested window (UTC).
            endtime: End of the requested window (UTC).

        Returns:
            The parsed seismogram: from the file on a hit, freshly fetched
            and stored on a miss.
        """
        key = _fetch_key(station, starttime, endtime)
        raw = self._cache.get(
            key,
            lambda: self.fetch_raw(
                station=station, starttime=starttime, endtime=endtime
            ),
        )
        return self.parse(raw)


def _fetch_key(station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp) -> str:
    # json.dumps escapes each field, so a value containing the delimiter
    # can't collide with another station/window. Timestamps are normalised to
    # UTC so two spellings of the same instant produce the same key.
    return json.dumps(
        [
            station.network,
            station.name,
            station.location,
            station.channel,
            convert_to_utc_timestamp(starttime).isoformat(),
            convert_to_utc_timestamp(endtime).isoformat(),
        ]
    )
