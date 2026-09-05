"""Tests for pysmo.tools.archive."""

import gc
import pickle
import sqlite3
import sys
import zlib
from pathlib import Path

import pandas as pd
import pytest

from pysmo import MiniSeismogram, MiniStation, Seismogram, Station
from pysmo.classes import SAC
from pysmo.tools.archive import (
    _CREATE_CACHE_INSERT_TRIGGER,
    SqliteArchiveFetcher,
)
from pysmo.tools.web import fetch_sac

RAW_BYTES = b"1.0,2.0,3.0"

FETCH_CALLS: list[tuple[str, str, pd.Timestamp, pd.Timestamp]] = []


def fake_fetch_raw(
    *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> bytes:
    """Module-level (not a closure) stand-in for a raw fetch function."""
    FETCH_CALLS.append((station.channel, station.name, starttime, endtime))
    return RAW_BYTES


def fake_parse(raw: bytes) -> Seismogram:
    data = [float(x) for x in raw.decode().split(",")]
    return MiniSeismogram(
        begin_time=pd.Timestamp("2024-01-01T00:00:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=data,
    )


@pytest.fixture(autouse=True)
def _reset_fetch_calls() -> None:
    FETCH_CALLS.clear()


@pytest.fixture()
def station() -> MiniStation:
    return MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="LHZ",
        latitude=34.945981,
        longitude=-106.457133,
    )


@pytest.fixture()
def starttime() -> pd.Timestamp:
    return pd.Timestamp("2024-01-01T00:00:00Z")


@pytest.fixture()
def endtime() -> pd.Timestamp:
    return pd.Timestamp("2024-01-01T00:01:00Z")


@pytest.fixture()
def archive(tmp_path: Path) -> SqliteArchiveFetcher:
    return SqliteArchiveFetcher(
        path=tmp_path / "archive.sqlite3",
        fetch_raw=fake_fetch_raw,
        parse=fake_parse,
    )


class TestCaching:
    def test_miss_then_hit(
        self,
        archive: SqliteArchiveFetcher,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        first = archive(station, starttime, endtime)
        second = archive(station, starttime, endtime)

        assert len(FETCH_CALLS) == 1
        assert list(first.data) == list(second.data) == [1.0, 2.0, 3.0]

    def test_distinct_keys_both_fetched(
        self,
        archive: SqliteArchiveFetcher,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        other_station = MiniStation(
            name=station.name,
            network=station.network,
            location=station.location,
            channel="LHN",
            latitude=station.latitude,
            longitude=station.longitude,
        )

        archive(station, starttime, endtime)
        archive(other_station, starttime, endtime)

        assert len(FETCH_CALLS) == 2

    def test_compression_round_trip(
        self,
        archive: SqliteArchiveFetcher,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        archive(station, starttime, endtime)
        cached = archive(station, starttime, endtime)

        assert list(cached.data) == [1.0, 2.0, 3.0]


class TestEncodingVersion:
    def test_mismatched_version_raises(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        path = tmp_path / "archive.sqlite3"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE cache (key TEXT PRIMARY KEY, data BLOB NOT NULL)")
        conn.execute("PRAGMA user_version = 999")
        conn.commit()
        conn.close()

        archive = SqliteArchiveFetcher(
            path=path, fetch_raw=fake_fetch_raw, parse=fake_parse
        )
        with pytest.raises(ValueError, match="user_version"):
            archive(station, starttime, endtime)

    def test_mismatched_version_does_not_mutate_schema(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        path = tmp_path / "archive.sqlite3"
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA user_version = 999")
        conn.commit()
        conn.close()

        archive = SqliteArchiveFetcher(
            path=path, fetch_raw=fake_fetch_raw, parse=fake_parse
        )
        with pytest.raises(ValueError, match="user_version"):
            archive(station, starttime, endtime)

        conn = sqlite3.connect(path)
        objects = conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'trigger')"
        ).fetchall()
        conn.close()
        assert objects == []


class TestWalFlag:
    def test_default_is_not_wal(
        self,
        archive: SqliteArchiveFetcher,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        archive(station, starttime, endtime)
        mode = archive._connect().execute("PRAGMA journal_mode").fetchone()[0]
        assert mode != "wal"

    def test_wal_true_enables_wal(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            wal=True,
        )
        archive(station, starttime, endtime)
        mode = archive._connect().execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"


class TestClose:
    def test_close_drops_connection_and_is_idempotent(
        self,
        archive: SqliteArchiveFetcher,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        archive(station, starttime, endtime)
        assert archive._conn is not None

        archive.close()
        assert archive._conn is None

        archive.close()  # no-op, must not raise
        assert archive._conn is None

    def test_garbage_collection_closes_connection_without_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )
        archive(station, starttime, endtime)

        # sqlite3 raises ResourceWarning from the connection's own finaliser,
        # which surfaces via sys.unraisablehook rather than the warnings filter.
        unraisable: list[object] = []
        monkeypatch.setattr(sys, "unraisablehook", unraisable.append)
        del archive
        gc.collect()

        assert unraisable == []


class TestConcurrentWriteRace:
    def test_insert_or_ignore_does_not_raise_on_collision(
        self, archive: SqliteArchiveFetcher, station: MiniStation
    ) -> None:
        starttime = pd.Timestamp("2024-01-01T00:00:00Z")
        endtime = pd.Timestamp("2024-01-01T00:01:00Z")
        key = archive._key(station, starttime, endtime)
        conn = archive._connect()

        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO cache (key, data) VALUES (?, ?)",
                (key, b"first"),
            )
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO cache (key, data) VALUES (?, ?)",
                (key, b"second"),
            )

        rows = conn.execute("SELECT data FROM cache WHERE key = ?", (key,)).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == b"first"


class TestPickling:
    def test_connection_dropped_and_reusable(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        path = tmp_path / "archive.sqlite3"
        archive = SqliteArchiveFetcher(
            path=path, fetch_raw=fake_fetch_raw, parse=fake_parse
        )
        archive(station, starttime, endtime)
        assert archive._conn is not None

        restored: SqliteArchiveFetcher = pickle.loads(pickle.dumps(archive))
        assert restored._conn is None

        # Simulate unpickling on a machine without the database file. The
        # original connection must be closed first, or Windows refuses to
        # unlink a file that still has an open handle.
        archive.close()
        path.unlink()
        result = restored(station, starttime, endtime)
        assert list(result.data) == [1.0, 2.0, 3.0]

    def test_equality_ignores_connection_state(self, tmp_path: Path) -> None:
        path = tmp_path / "archive.sqlite3"
        used = SqliteArchiveFetcher(
            path=path, fetch_raw=fake_fetch_raw, parse=fake_parse
        )
        unused = SqliteArchiveFetcher(
            path=path, fetch_raw=fake_fetch_raw, parse=fake_parse
        )
        used._connect()  # opens a live connection; `unused` never does

        assert used == unused


class TestPersistentConnection:
    def test_connection_reused_across_calls(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        real_connect = sqlite3.connect
        calls: list[Path] = []

        def spy_connect(
            database: Path, timeout: float = 5.0, check_same_thread: bool = True
        ) -> sqlite3.Connection:
            calls.append(database)
            return real_connect(
                database, timeout=timeout, check_same_thread=check_same_thread
            )

        monkeypatch.setattr("pysmo.tools.archive.sqlite3.connect", spy_connect)

        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )
        archive(station, starttime, endtime)
        archive(station, starttime, endtime)

        assert len(calls) == 1


class TestConstructionTimeValidation:
    def test_missing_parent_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            SqliteArchiveFetcher(
                path=tmp_path / "missing" / "archive.sqlite3",
                fetch_raw=fake_fetch_raw,
                parse=fake_parse,
            )

    def test_existing_parent_directory_ok(self, tmp_path: Path) -> None:
        SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )

    @pytest.mark.parametrize("max_bytes", [-1, 0])
    def test_non_positive_max_bytes_raises(
        self, tmp_path: Path, max_bytes: int
    ) -> None:
        with pytest.raises(ValueError, match="max_bytes"):
            SqliteArchiveFetcher(
                path=tmp_path / "archive.sqlite3",
                fetch_raw=fake_fetch_raw,
                parse=fake_parse,
                max_bytes=max_bytes,
            )


class TestMaxBytes:
    """FIFO eviction via max_bytes."""

    def _count_rows(self, archive: SqliteArchiveFetcher) -> int:
        return archive._connect().execute("SELECT COUNT(*) FROM cache").fetchone()[0]

    def _total_bytes(self, archive: SqliteArchiveFetcher) -> int:
        result = (
            archive._connect()
            .execute("SELECT COALESCE(SUM(length(data)), 0) FROM cache")
            .fetchone()[0]
        )
        return int(result)

    def _one_entry_bytes(
        self, tmp_path: Path, station: MiniStation, starttime: pd.Timestamp
    ) -> int:
        """Measure the compressed size of a single cached entry."""
        probe = SqliteArchiveFetcher(
            path=tmp_path / "probe.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )
        probe(station, starttime, starttime + pd.Timedelta(minutes=1))
        size = self._total_bytes(probe)
        probe.close()
        return size

    def test_default_is_unlimited(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )
        for i in range(10):
            t = starttime + pd.Timedelta(minutes=i)
            archive(station, t, t + pd.Timedelta(minutes=1))

        assert self._count_rows(archive) == 10

    def test_evicts_oldest_when_limit_exceeded(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        limit = one_entry_bytes * 2
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=limit,
        )

        for i in range(5):
            s = starttime + pd.Timedelta(minutes=i)
            archive(station, s, s + pd.Timedelta(minutes=1))

        # Eviction targets the low-water mark (75% of the limit), so a burst
        # into a 2-entry cache ends holding only the newest entry.
        assert self._count_rows(archive) == 1
        assert self._total_bytes(archive) <= limit

    def test_oldest_entry_is_gone_after_eviction(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)

        # One-entry limit: every new write evicts the previous one.
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=one_entry_bytes,
        )
        archive(station, t0, t1)
        archive(station, t2, t3)

        conn = archive._connect()
        key_old = SqliteArchiveFetcher._key(station, t0, t1)
        key_new = SqliteArchiveFetcher._key(station, t2, t3)
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM cache WHERE key = ?", (key_old,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM cache WHERE key = ?", (key_new,)
            ).fetchone()[0]
            == 1
        )

    def test_oversized_entry_is_kept_not_thrashed(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """An entry larger than max_bytes must not be evicted immediately.

        If it were, fetch_raw would be called on every subsequent access,
        breaking the "only ever fetched once" guarantee.
        """
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        FETCH_CALLS.clear()  # exclude the probe fetch from the count
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)

        # Limit smaller than a single entry.
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=one_entry_bytes - 1,
        )
        archive(station, t0, t1)  # miss — fetches and stores
        archive(station, t0, t1)  # must be a hit, NOT a second fetch

        assert len(FETCH_CALLS) == 1
        assert self._count_rows(archive) == 1

    def test_evicted_entry_refetched_on_next_access(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """After eviction, a subsequent access to the evicted key re-fetches."""
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        FETCH_CALLS.clear()  # exclude the probe fetch from the count
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)

        # One-entry limit: inserting t2 evicts t0.
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=one_entry_bytes,
        )
        archive(station, t0, t1)  # fetch #1
        archive(station, t2, t3)  # fetch #2, evicts t0
        archive(station, t0, t1)  # t0 gone — must re-fetch (#3)

        assert len(FETCH_CALLS) == 3

    def test_no_shrink_on_read_only_access(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """Reopening an already-over-limit cache never evicts on the hit path."""
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        FETCH_CALLS.clear()  # exclude the probe fetch from the count
        path = tmp_path / "archive.sqlite3"

        # Fill the cache with two entries while unlimited.
        fill = SqliteArchiveFetcher(
            path=path,
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)
        fill(station, t0, t1)
        fill(station, t2, t3)
        fill.close()

        # Reopen with a limit smaller than the existing total.
        restricted = SqliteArchiveFetcher(
            path=path,
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=one_entry_bytes,
        )
        restricted(station, t0, t1)  # hit — must not evict
        restricted(station, t2, t3)  # hit — must not evict

        assert len(FETCH_CALLS) == 2  # only the two fill() fetches
        assert self._count_rows(restricted) == 2  # both entries still present

    def test_legacy_database_bootstrapped_and_evicted(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """A legacy database with existing rows bootstraps cache_stats and evicts."""
        path = tmp_path / "legacy.sqlite3"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE cache (key TEXT PRIMARY KEY, data BLOB NOT NULL)")
        conn.execute("PRAGMA user_version = 1")
        k1 = SqliteArchiveFetcher._key(
            station, starttime, starttime + pd.Timedelta(minutes=1)
        )
        k2 = SqliteArchiveFetcher._key(
            station,
            starttime + pd.Timedelta(minutes=1),
            starttime + pd.Timedelta(minutes=2),
        )
        blob = zlib.compress(RAW_BYTES)
        conn.execute("INSERT INTO cache (key, data) VALUES (?, ?)", (k1, blob))
        conn.execute("INSERT INTO cache (key, data) VALUES (?, ?)", (k2, blob))
        conn.commit()
        conn.close()

        limit = len(blob) * 2
        archive = SqliteArchiveFetcher(
            path=path,
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=limit,
        )
        conn = archive._connect()
        stats_bytes = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()[0]
        assert stats_bytes == len(blob) * 2

        FETCH_CALLS.clear()
        archive(
            station,
            starttime + pd.Timedelta(minutes=2),
            starttime + pd.Timedelta(minutes=3),
        )
        # The two legacy rows are evicted (down to the low-water mark), leaving
        # only the freshly inserted entry.
        assert self._count_rows(archive) == 1
        assert self._total_bytes(archive) <= limit
        assert (
            conn.execute("SELECT COUNT(*) FROM cache WHERE key = ?", (k1,)).fetchone()[
                0
            ]
            == 0
        )

    def test_missing_cache_stats_row_heals(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """Deleting the cache_stats row does not crash and lazily heals."""
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=1000,
        )
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)
        archive(station, t0, t1)

        conn = archive._connect()
        with conn:
            conn.execute("DELETE FROM cache_stats")

        FETCH_CALLS.clear()
        archive(station, t2, t3)
        assert len(FETCH_CALLS) == 1
        stats_bytes = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()
        assert stats_bytes is not None
        assert stats_bytes[0] == self._total_bytes(archive)

    def test_negative_stats_total_heals(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """A negative cache_stats total is never legitimate and must rebuild."""
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        FETCH_CALLS.clear()
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=one_entry_bytes,
        )
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)
        archive(station, t0, t1)

        conn = archive._connect()
        # Simulate a stale counter (e.g. trigger-driven deletes of rows that
        # were never counted) that has gone negative.
        with conn:
            conn.execute("UPDATE cache_stats SET total_bytes = -1000 WHERE id = 1")

        FETCH_CALLS.clear()
        archive(station, t2, t3)

        # The negative total must be treated as stale: rebuilt from ground
        # truth, then eviction proceeds (and heals) normally.
        assert len(FETCH_CALLS) == 1
        assert self._count_rows(archive) == 1
        assert self._total_bytes(archive) <= one_entry_bytes
        stats_bytes = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()[0]
        assert stats_bytes == self._total_bytes(archive)

    def test_bypass_desync_heals_on_eviction(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """If cache_stats desyncs, eviction re-checks ground truth and heals."""
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        FETCH_CALLS.clear()
        limit = one_entry_bytes * 2
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=limit,
        )
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)
        t4, t5 = t3, starttime + pd.Timedelta(minutes=3)
        t6, t7 = t5, starttime + pd.Timedelta(minutes=4)
        archive(station, t0, t1)
        archive(station, t2, t3)

        conn = archive._connect()
        # Drop the insert trigger to simulate an external write or bypass
        with conn:
            conn.execute("DROP TRIGGER cache_insert_bytes")
            # Uncounted insert: real total becomes 3 entries, but stats says 2
            blob = zlib.compress(RAW_BYTES)
            key_uncounted = SqliteArchiveFetcher._key(station, t4, t5)
            conn.execute(
                "INSERT INTO cache (key, data) VALUES (?, ?)",
                (key_uncounted, blob),
            )

        # Re-add trigger as would happen on reconnect
        with conn:
            conn.execute(_CREATE_CACHE_INSERT_TRIGGER)

        # Next insert via archive pushes stats over limit.
        # Eviction re-checks ground truth, evicts below the low-water mark and
        # reconciles cache_stats with the real total.
        archive(station, t6, t7)
        assert self._count_rows(archive) == 1
        assert self._total_bytes(archive) <= limit
        stats_bytes = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()[0]
        assert stats_bytes == self._total_bytes(archive)

    def test_bypass_desync_under_cap_not_healed_until_crossing(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        """Under-cap bypass writes do not heal until the tracked total crosses limit.

        Documents the architectural trade-off: inserts remain O(1) by trusting
        triggers, so uncounted external writes remain unhealed while tracked
        total is below max_bytes. Once tracked total crosses max_bytes,
        eviction engages, re-verifies ground truth, and heals.
        """
        one_entry_bytes = self._one_entry_bytes(tmp_path, station, starttime)
        FETCH_CALLS.clear()
        # Allow 4 entries
        limit = one_entry_bytes * 4
        archive = SqliteArchiveFetcher(
            path=tmp_path / "archive.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=limit,
        )
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)
        t4, t5 = t3, starttime + pd.Timedelta(minutes=3)
        t6, t7 = t5, starttime + pd.Timedelta(minutes=4)
        t8, t9 = t7, starttime + pd.Timedelta(minutes=5)
        archive(station, t0, t1)
        archive(station, t2, t3)

        conn = archive._connect()
        # Drop trigger and insert uncounted rows
        with conn:
            conn.execute("DROP TRIGGER cache_insert_bytes")
            blob = zlib.compress(RAW_BYTES)
            conn.execute(
                "INSERT INTO cache (key, data) VALUES (?, ?)",
                (SqliteArchiveFetcher._key(station, t4, t5), blob),
            )
            conn.execute(
                "INSERT INTO cache (key, data) VALUES (?, ?)",
                (SqliteArchiveFetcher._key(station, t6, t7), blob),
            )
            # Re-create trigger
            conn.execute(_CREATE_CACHE_INSERT_TRIGGER)

        # Real table has 4 entries (limit), but stats only tracked 2 entries.
        # Inserting a 5th entry via archive increases tracked stats to 3 (< limit).
        archive(station, t8, t9)
        # Because tracked stats <= limit, O(1) fast-path skips table scan;
        # the cache temporarily holds 5 entries (> limit).
        assert self._count_rows(archive) == 5

        # Inserting two more entries pushes tracked stats past limit.
        t10, t11 = t9, starttime + pd.Timedelta(minutes=6)
        t12, t13 = t11, starttime + pd.Timedelta(minutes=7)
        archive(station, t10, t11)
        archive(station, t12, t13)

        # Now eviction has engaged: ground truth was verified, older entries
        # were evicted down to the low-water mark, and total is strictly
        # <= limit.
        assert self._count_rows(archive) == 3
        assert self._total_bytes(archive) <= limit
        stats_bytes = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()[0]
        assert stats_bytes == self._total_bytes(archive)


def test_fetch_mseed_pairing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    station: MiniStation,
    reference_event_assets: dict[str, Path],
) -> None:
    """The recommended reproducible-fetch pairing for PysmoProject's default format."""
    from pysmo.classes import MSeed
    from pysmo.tools.web import fetch_mseed

    http_calls: list[object] = []

    def fake_http_get(url: str, fields: dict[str, object], **kwargs: object) -> bytes:
        http_calls.append(fields)
        return reference_event_assets["mseed_bhz"].read_bytes()

    monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

    archive = SqliteArchiveFetcher(
        path=tmp_path / "archive.sqlite3",
        fetch_raw=fetch_mseed,
        parse=MSeed.from_bytes,
    )
    starttime = pd.Timestamp("2010-02-27T06:44:00Z")
    endtime = pd.Timestamp("2010-02-27T06:54:00Z")

    first = archive(station, starttime, endtime)
    second = archive(station, starttime, endtime)

    assert len(http_calls) == 1  # second call served from the sqlite archive
    assert isinstance(first, MSeed)
    assert (first.data == second.data).all()


@pytest.mark.real_web_request
def test_fetch_sac_pairing_live(tmp_path: Path, station: MiniStation) -> None:
    def parse_sac_zip(raw: bytes) -> Seismogram:
        return SAC.from_zip(raw).seismogram

    archive = SqliteArchiveFetcher(
        path=tmp_path / "archive.sqlite3", fetch_raw=fetch_sac, parse=parse_sac_zip
    )
    starttime = pd.Timestamp("2010-02-27T06:44:00Z")
    endtime = pd.Timestamp("2010-02-27T06:54:00Z")

    first = archive(station, starttime, endtime)
    second = archive(station, starttime, endtime)

    assert (first.data == second.data).all()
