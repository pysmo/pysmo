"""Local archives for raw FDSN fetch responses.

An archive fetcher wraps a raw-bytes fetch function (e.g.
[`fetch_sac`][pysmo.tools.web.fetch_sac],
[`fetch_geocsvseismogram`][pysmo.tools.web.fetch_geocsvseismogram]) with
persistent storage, so a station/time-window combination already fetched
once is read back locally rather than re-fetched.

Particularly useful as
[`PysmoProject.fetch_seismogram`][pysmo.tools.project.PysmoProject.fetch_seismogram],
so a project's entries are only ever fetched once across however many times
the project is used.

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
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
from attrs import define, field

from pysmo import Seismogram, Station
from pysmo._utils import attrs_getstate, attrs_setstate
from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = ["RawFetcher", "RawParser", "SqliteArchiveFetcher"]

_ENCODING_VERSION = 1
"""Raw bytes are stored zlib-compressed; bump this on any change to that encoding."""


class RawFetcher(Protocol):
    """Callable `(*, station, starttime, endtime) -> bytes` returning a raw, unparsed fetch response.

    A `Protocol` with a keyword-only `__call__`, not a plain `Callable[...]`
    type alias, specifically because the functions this slot is meant to be
    filled with directly — [`fetch_sac`][pysmo.tools.web.fetch_sac] and
    [`fetch_geocsvseismogram`][pysmo.tools.web.fetch_geocsvseismogram] — are
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
is paired with — nothing enforces this pairing statically, the same as
`fetch_sac`/`SAC.from_zip` are already paired by convention today.
"""


@define(kw_only=True)
class SqliteArchiveFetcher:
    """Caches raw fetch responses in one local SQLite database.

    Format-agnostic: stores whatever bytes `fetch_raw` returns
    (zlib-compressed), keyed by station identity and time window, and hands
    the decompressed bytes to `parse` on both a cache hit and a miss. A hit
    never calls `fetch_raw` again — a side effect of this is bit-identical
    replay of a previously fetched window, rather than only detecting drift
    after the fact. `fetch_raw` runs outside the lock, so two threads racing
    the same not-yet-cached window both fetch before one result is stored.

    Warning: Local disk only
        SQLite's own documentation states that WAL mode does not work over a
        network filesystem, and recommends against concurrent multi-process
        access to a SQLite database over NFS at all. This class assumes the
        database file lives on local disk with correctly functioning file
        locking; it is not a safe choice for a cache shared over a network
        filesystem by more than one process at a time.
    """

    path: Path = field(converter=Path)
    """Location of the SQLite database file.

    The file itself is created on first use if it doesn't exist; its
    *parent directory* must already exist, checked at construction time.
    """

    fetch_raw: RawFetcher
    """Fetches a raw response for a station and absolute time window."""

    parse: RawParser
    """Parses a raw response (freshly fetched, or read back from cache) into a `Seismogram`."""

    wal: bool = False
    """Enable WAL mode. Only for a database confirmed to be on local disk — see the class docstring."""

    _conn: sqlite3.Connection | None = field(
        init=False, default=None, repr=False, eq=False
    )
    _lock: threading.Lock = field(
        init=False, factory=threading.Lock, repr=False, eq=False
    )
    """Guards the check-then-set on `_conn`: `check_same_thread=False` means
    this instance may legitimately be called from more than one thread, and
    without this lock two threads racing the first call could each open
    their own connection, silently leaking one."""

    def __attrs_post_init__(self) -> None:
        """Fail fast if `path`'s parent directory doesn't exist."""
        if not self.path.parent.is_dir():
            raise FileNotFoundError(
                f"Parent directory does not exist: {self.path.parent}"
            )

    def __getstate__(self) -> dict[str, Any]:
        """Drop the live connection; the lock is excluded entirely below (no `threading.Lock` is picklable, not even a fresh one)."""
        state = attrs_getstate(self, {"_conn": None})
        del state["_lock"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore state without triggering any `on_setattr` hooks, then create a fresh lock."""
        attrs_setstate(self, state)
        object.__setattr__(self, "_lock", threading.Lock())

    def close(self) -> None:
        """Close the underlying connection, if one is open.

        Not required before the object is garbage-collected or the process
        exits — normal teardown closes the file descriptor regardless — but
        call it explicitly to release the connection sooner in a
        long-running process holding many such fetchers.
        """
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def _connect(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
                if self.wal:
                    conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS cache "
                    + "(key TEXT PRIMARY KEY, data BLOB NOT NULL)"
                )
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
                self._conn = conn
            return self._conn

    def __call__(
        self, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> Seismogram:
        """Return a `Seismogram` for `station` and window, from cache if already fetched.

        Args:
            station: Station to fetch data for.
            starttime: Start of the requested window (UTC).
            endtime: End of the requested window (UTC).

        Returns:
            Parsed result — from the cache database on a hit, freshly
            fetched (and then stored) on a miss.
        """
        key = self._key(station, starttime, endtime)
        conn = self._connect()
        row = conn.execute("SELECT data FROM cache WHERE key = ?", (key,)).fetchone()
        if row is not None:
            return self.parse(zlib.decompress(row[0]))
        raw = self.fetch_raw(station=station, starttime=starttime, endtime=endtime)
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO cache (key, data) VALUES (?, ?)",
                (key, zlib.compress(raw)),
            )
        return self.parse(raw)

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
