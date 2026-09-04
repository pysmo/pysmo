"""Local archives for raw FDSN fetch responses.

An archive fetcher wraps a raw-bytes fetch function (e.g.
[`fetch_sac`][pysmo.tools.web.fetch_sac],
[`fetch_geocsvseismogram`][pysmo.tools.web.fetch_geocsvseismogram]) with
persistent storage, so a station/time-window combination already fetched
once is read back locally rather than re-fetched.

Particularly useful as
[`PysmoProject.fetch_seismogram`][pysmo.tools.project.PysmoProject.fetch_seismogram],
so a project's entries are only ever fetched once across however many times
the project is used, provided entries remain in the cache (or when using an
unbounded cache).

Examples:
    [`SqliteArchiveFetcher`][pysmo.tools.archive.SqliteArchiveFetcher] stores
    responses in a local SQLite database. Paired here with
    [`fetch_sac`][pysmo.tools.web.fetch_sac] and
    [`SAC.from_zip`][pysmo.classes.SAC.from_zip]:

    <!-- skip: start if(not run_real_web_requests) -->
    ```python
    >>> import pandas as pd
    >>> from pysmo import MiniStation, Seismogram
    >>> from pysmo.classes import SAC
    >>> from pysmo.tools.archive import SqliteArchiveFetcher
    >>> from pysmo.tools.web import fetch_sac
    >>>
    >>> def parse_sac_zip(raw: bytes) -> Seismogram:
    ...     return SAC.from_zip(raw).seismogram
    ...
    >>> station = MiniStation(
    ...     name="ANMO", network="IU", location="00", channel="LHZ",
    ...     latitude=34.945981, longitude=-106.457133,
    ... )
    >>> starttime = pd.Timestamp("2010-02-27T06:44:00Z")
    >>> endtime = pd.Timestamp("2010-02-27T06:54:00Z")
    >>>
    >>> archive = SqliteArchiveFetcher(
    ...     path="project_cache.sqlite3", fetch_raw=fetch_sac, parse=parse_sac_zip
    ... )
    >>> seismogram = archive(station, starttime, endtime)  # miss: fetches and stores
    >>> seismogram_again = archive(station, starttime, endtime)  # hit: no fetch
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

__all__ = ["RawFetcher", "RawParser", "SqliteArchiveFetcher"]

_ENCODING_VERSION = 1
"""Raw bytes are stored zlib-compressed; bump this on any change to that encoding."""

_LOW_WATER_FRACTION = 0.75
"""Eviction target ratio of `max_bytes`.

When the limit is crossed, the oldest entries are evicted until at most this
fraction of `max_bytes` remains. The slack means a full cache does not
re-check ground truth on every single miss; consecutive misses are O(1)
between evictions."""

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
"""Schema DDL shared with the tests so the two cannot diverge."""


class RawFetcher(Protocol):
    """Callable `(*, station, starttime, endtime) -> bytes` for a raw fetch response.

    A `Protocol` with a keyword-only `__call__`, not a plain `Callable[...]`
    type alias, specifically because the functions this slot is meant to be
    filled with directly ([`fetch_sac`][pysmo.tools.web.fetch_sac] and
    [`fetch_geocsvseismogram`][pysmo.tools.web.fetch_geocsvseismogram]) are
    themselves keyword-only. A plain positional `Callable` type cannot
    express that, and calling one positionally raises `TypeError` regardless
    of what a type checker allows.
    """

    def __call__(
        self, *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> bytes:
        """Fetch raw bytes for a station and absolute time window."""
        ...


type RawParser = Callable[[bytes], Seismogram]
"""Callable `(raw) -> Seismogram` parsing a raw fetch response.

E.g. a wrapper around [`SAC.from_zip`][pysmo.classes.SAC.from_zip] or
[`GeoCsvSeismogram.from_text`][pysmo.classes.GeoCsvSeismogram.from_text].
Must agree with whichever [`RawFetcher`][pysmo.tools.archive.RawFetcher] it
is paired with; nothing enforces this pairing statically, the same as
`fetch_sac`/`SAC.from_zip` are already paired by convention today.
"""


@define(kw_only=True)
class SqliteArchiveFetcher:
    """Caches raw fetch responses in one local SQLite database.

    Format-agnostic: stores whatever bytes `fetch_raw` returns
    (zlib-compressed), keyed by station identity and time window, and hands
    the decompressed bytes to `parse` on both a cache hit and a miss. While
    an entry remains in the cache (or when `max_bytes=None`), a hit never
    calls `fetch_raw` again; a side effect of this is bit-identical replay of a
    previously fetched window, rather than only detecting drift after the fact.
    If an entry is evicted under a finite `max_bytes`, subsequent access will
    re-fetch it. `fetch_raw` runs outside the lock, so two threads racing
    the same not-yet-cached window both fetch before one result is stored.

    Warning: Local disk only
        SQLite's own documentation states that WAL mode does not work over a
        network filesystem, and recommends against concurrent multi-process
        access to a SQLite database over NFS at all. This class assumes the
        database file lives on local disk with correctly functioning file
        locking; it is not a safe choice for a cache shared over a network
        filesystem by more than one process at a time. Concurrent writers to
        the same file may transiently desynchronise the `cache_stats`
        counter; it self-heals on the next eviction's ground-truth re-check.
    """

    path: Path = field(converter=Path)
    """Location of the SQLite database file.

    The file itself is created on first use if it doesn't exist; its
    *parent directory* must already exist, checked at construction time.
    """

    fetch_raw: RawFetcher
    """Fetch a raw response for a station and absolute time window."""

    parse: RawParser
    """Parse a raw response (freshly fetched or from cache) into a `Seismogram`."""

    wal: bool = False
    """Enable WAL mode.

    Only for a database confirmed to be on local disk (see the class docstring).
    """

    max_bytes: PositiveInt | None = field(
        default=None,
        validator=validators.optional(validators.gt(0)),
    )
    """Maximum total size of compressed data stored in the cache, in bytes.

    When a newly cached entry causes the total to exceed this limit, the
    oldest entries (by insertion order) are evicted until the cache fits
    within the limit again. If a single entry's compressed size exceeds
    `max_bytes`, it is stored and kept rather than immediately evicted, so
    the cache will hold exactly that one entry and every older entry will
    be removed. Leave as `None` for unlimited storage.

    Note: Compressed payload, trigger contract and eviction cost
        This limit applies to the raw compressed `data` column bytes only.
        Actual on-disk usage is higher due to SQLite page, B-tree index, and
        WAL overhead; the real file will exceed `max_bytes` by a small
        constant amount. Cache size is tracked using an internal
        `cache_stats` table and database triggers, keeping hits and
        under-limit misses O(1). Crossing the limit runs a ground-truth
        re-check (an O(rows) pass) and evicts the oldest entries down to 75%
        of `max_bytes`, so evictions are amortised over each quarter of
        capacity rather than paid on every miss. Existing databases are
        upgraded transparently without altering `user_version`. Direct
        external writes that bypass the database triggers can cause tracked
        size to lag until the counter crosses `max_bytes` and triggers
        ground-truth verification. Entry order is SQLite's `rowid`, which
        reproduces insertion order except after `VACUUM` or external row
        writes.

    Defaults to unlimited (`None`), matching a project's expectation that
    a cached entry is never silently dropped and re-fetched.
    """

    _conn: sqlite3.Connection | None = field(
        init=False, default=None, repr=False, eq=False
    )
    _lock: threading.Lock = field(
        init=False, factory=threading.Lock, repr=False, eq=False
    )
    """Guards `_conn` setup and `_store`: `check_same_thread=False` means this
    instance may legitimately be called from more than one thread. Without
    the first guard, two threads racing the first call could each open their
    own connection, silently leaking one. Without the second, two threads
    sharing one connection could interleave writes into the same implicit
    transaction, corrupting the `cache_stats` total or losing an insert to
    another thread's rollback."""

    def __attrs_post_init__(self) -> None:
        """Fail fast if `path`'s parent directory doesn't exist."""
        if not self.path.parent.is_dir():
            raise FileNotFoundError(
                f"Parent directory does not exist: {self.path.parent}"
            )

    def __getstate__(self) -> dict[str, Any]:
        """Drop the live connection for pickling.

        The lock is excluded entirely below; no `threading.Lock` is picklable,
        not even a fresh one.
        """
        state = attrs_getstate(self, {"_conn": None})
        del state["_lock"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore state without firing `on_setattr` hooks, then make a fresh lock."""
        attrs_setstate(self, state)
        object.__setattr__(self, "_lock", threading.Lock())

    def close(self) -> None:
        """Close the underlying connection, if one is open.

        Not required for correctness, since `__del__` closes it on garbage
        collection. Call it explicitly to release the connection sooner in a
        long-running process holding many such fetchers.
        """
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __del__(self) -> None:
        """Close the connection on garbage collection.

        `sqlite3` emits a `ResourceWarning` if it has to finalise a live
        connection itself, so close it here rather than leave it to the
        connection's own finaliser. No lock is taken, since nothing else can
        hold a reference by the time this runs.
        """
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
                    conn.execute(f"PRAGMA user_version = {_ENCODING_VERSION}")
                elif version != _ENCODING_VERSION:
                    conn.close()
                    raise ValueError(
                        f"{self.path} was written with a different cache "
                        + f"encoding (user_version={version}, expected "
                        + f"{_ENCODING_VERSION})."
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

    def __call__(
        self, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> Seismogram:
        """Return a `Seismogram` for `station` and window, from cache when possible.

        Args:
            station: Station to fetch data for.
            starttime: Start of the requested window (UTC).
            endtime: End of the requested window (UTC).

        Returns:
            Parsed result: from the cache database on a hit, freshly
            fetched (and then stored) on a miss.
        """
        key = self._key(station, starttime, endtime)
        conn = self._connect()
        row = conn.execute("SELECT data FROM cache WHERE key = ?", (key,)).fetchone()
        if row is not None:
            return self.parse(zlib.decompress(row[0]))
        raw = self.fetch_raw(station=station, starttime=starttime, endtime=endtime)
        self._store(conn, key, zlib.compress(raw))
        return self.parse(raw)

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

    @staticmethod
    def _key(station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp) -> str:
        # json.dumps rather than an f-string join: unambiguously escapes each
        # field, so a field value containing the join delimiter can't collide
        # with a different station/window's key. Timestamps are normalised
        # to UTC first so two representations of the same instant (e.g.
        # +00:00 vs +01:00) hash to the same key.
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
