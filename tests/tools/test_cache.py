"""Tests for pysmo.tools.cache."""

import gc
import pickle
import sqlite3
import sys
import zlib
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest
from attrs import define

from pysmo import MiniSeismogram, MiniStation, Seismogram, Station
from pysmo.classes import SAC
from pysmo.tools.cache import (
    _CREATE_CACHE_INSERT_TRIGGER,
    BlobCache,
    FetchCache,
    _fetch_key,
)
from pysmo.tools.web import fetch_sac

RAW_BYTES = b"1.0,2.0,3.0"


def _const(value: bytes) -> Callable[[], bytes]:
    """A `produce` thunk returning a fixed payload."""
    return lambda: value


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
def cache(tmp_path: Path) -> FetchCache:
    return FetchCache(
        path=tmp_path / "cache.sqlite3",
        fetch_raw=fake_fetch_raw,
        parse=fake_parse,
    )


class TestEngine:
    """The byte-oriented BlobCache engine."""

    def test_miss_produces_then_hit_does_not(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        calls: list[int] = []

        def produce() -> bytes:
            calls.append(1)
            return b"\x00\x01payload\xff"

        first = engine.get("k", produce)
        second = engine.get("k", produce)

        assert first == second == b"\x00\x01payload\xff"
        assert len(calls) == 1

    def test_stored_bytes_are_compressed_on_disk(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        payload = b"x" * 5000
        engine.get("k", lambda: payload)

        row = engine._connect().execute("SELECT data FROM cache").fetchone()
        assert row[0] != payload
        assert zlib.decompress(row[0]) == payload
        assert len(row[0]) < len(payload)

    def test_arbitrary_binary_round_trips(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        payload = bytes(range(256)) * 4
        assert engine.get("k", lambda: payload) == payload
        assert engine.get("k", lambda: b"unused") == payload

    def test_distinct_keys_are_independent(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        assert engine.get("a", lambda: b"aaa") == b"aaa"
        assert engine.get("b", lambda: b"bbb") == b"bbb"
        assert engine.get("a", lambda: b"unused") == b"aaa"

    def test_mismatched_encoding_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "e.sqlite3"
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA user_version = 999")
        conn.commit()
        conn.close()

        engine = BlobCache(path=path, encoding_version=1)
        with pytest.raises(ValueError, match="user_version"):
            engine.get("k", lambda: b"x")

    def test_mismatched_version_does_not_mutate_schema(self, tmp_path: Path) -> None:
        path = tmp_path / "e.sqlite3"
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA user_version = 999")
        conn.commit()
        conn.close()

        engine = BlobCache(path=path, encoding_version=1)
        with pytest.raises(ValueError, match="user_version"):
            engine.get("k", lambda: b"x")

        conn = sqlite3.connect(path)
        objects = conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'trigger')"
        ).fetchall()
        conn.close()
        assert objects == []

    def test_pickling_drops_connection_and_stays_usable(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        engine.get("k", lambda: b"payload")
        assert engine._conn is not None

        restored: BlobCache = pickle.loads(pickle.dumps(engine))
        assert restored._conn is None

        engine.close()
        (tmp_path / "e.sqlite3").unlink()
        # Fresh file, same behaviour.
        assert restored.get("k", lambda: b"new") == b"new"

    def test_missing_parent_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            BlobCache(path=tmp_path / "missing" / "e.sqlite3", encoding_version=1)

    def test_wal_flag(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1, wal=True)
        engine.get("k", lambda: b"x")
        mode = engine._connect().execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    @pytest.mark.parametrize("max_bytes", [-1, 0])
    def test_non_positive_max_bytes_raises(
        self, tmp_path: Path, max_bytes: int
    ) -> None:
        with pytest.raises(ValueError, match="max_bytes"):
            BlobCache(
                path=tmp_path / "e.sqlite3", encoding_version=1, max_bytes=max_bytes
            )

    def test_evicts_oldest_to_low_water_mark(self, tmp_path: Path) -> None:
        one = len(zlib.compress(b"payload-0"))
        engine = BlobCache(
            path=tmp_path / "e.sqlite3", encoding_version=1, max_bytes=one * 2
        )
        for i in range(5):
            engine.get(f"k{i}", _const(f"payload-{i}".encode()))

        conn = engine._connect()
        rows = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        total = conn.execute(
            "SELECT COALESCE(SUM(length(data)), 0) FROM cache"
        ).fetchone()[0]
        assert rows == 1
        assert total <= one * 2

    def test_cache_stats_self_heals_on_uncounted_delete(self, tmp_path: Path) -> None:
        one = len(zlib.compress(b"payload-0"))
        engine = BlobCache(
            path=tmp_path / "e.sqlite3", encoding_version=1, max_bytes=one * 2
        )
        engine.get("k0", lambda: b"payload-0")
        engine.get("k1", lambda: b"payload-1")

        conn = engine._connect()
        with conn:
            conn.execute("DROP TRIGGER cache_delete_bytes")
            conn.execute("DELETE FROM cache WHERE key = 'k0'")
            conn.execute(_CREATE_CACHE_INSERT_TRIGGER)

        # Tracked total now overstates real usage; the next crossing heals it.
        engine.get("k2", lambda: b"payload-2")
        engine.get("k3", lambda: b"payload-3")
        stats = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()[0]
        real = conn.execute(
            "SELECT COALESCE(SUM(length(data)), 0) FROM cache"
        ).fetchone()[0]
        assert stats == real

    def test_negative_stats_total_heals(self, tmp_path: Path) -> None:
        one = len(zlib.compress(b"payload-0"))
        engine = BlobCache(
            path=tmp_path / "e.sqlite3", encoding_version=1, max_bytes=one
        )
        engine.get("k0", _const(b"payload-0"))

        conn = engine._connect()
        with conn:
            conn.execute("UPDATE cache_stats SET total_bytes = -1000 WHERE id = 1")

        # A negative total is never legitimate: rebuilt from ground truth,
        # then eviction proceeds normally.
        engine.get("k1", lambda: b"payload-1")
        assert conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0] == 1
        stats = conn.execute(
            "SELECT total_bytes FROM cache_stats WHERE id = 1"
        ).fetchone()[0]
        real = conn.execute(
            "SELECT COALESCE(SUM(length(data)), 0) FROM cache"
        ).fetchone()[0]
        assert stats == real <= one

    def test_oversized_entry_is_kept_not_thrashed(self, tmp_path: Path) -> None:
        """An entry larger than max_bytes must be stored and kept, not re-produced.

        If it were evicted immediately, `produce` would run on every call,
        breaking the guarantee a hit never re-produces.
        """
        payload = b"x" * 2000
        one = len(zlib.compress(payload))
        engine = BlobCache(
            path=tmp_path / "e.sqlite3", encoding_version=1, max_bytes=one - 1
        )
        calls: list[int] = []

        def produce() -> bytes:
            calls.append(1)
            return payload

        engine.get("k", produce)  # miss
        engine.get("k", produce)  # must be a hit

        assert calls == [1]
        assert (
            engine._connect().execute("SELECT COUNT(*) FROM cache").fetchone()[0] == 1
        )

    def test_reopening_over_limit_cache_does_not_evict_on_hit(
        self, tmp_path: Path
    ) -> None:
        """Eviction happens on insert, never on a read."""
        path = tmp_path / "e.sqlite3"
        one = len(zlib.compress(b"payload-0"))

        fill = BlobCache(path=path, encoding_version=1)  # unlimited
        fill.get("k0", lambda: b"payload-0")
        fill.get("k1", lambda: b"payload-1")
        fill.close()

        restricted = BlobCache(path=path, encoding_version=1, max_bytes=one)
        restricted.get("k0", lambda: b"unused")  # hit
        restricted.get("k1", lambda: b"unused")  # hit

        assert (
            restricted._connect().execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            == 2
        )

    def test_peek_and_put_are_get_split_in_two(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        assert engine.peek("k") is None
        engine.put("k", b"payload")
        assert engine.peek("k") == b"payload"
        engine.put("k", b"ignored")  # first write wins
        assert engine.peek("k") == b"payload"

    def test_write_failure_warns_and_returns_the_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)

        def boom(*_: object, **__: object) -> None:
            raise sqlite3.OperationalError("disk I/O error")

        monkeypatch.setattr(BlobCache, "_store", boom)
        with pytest.warns(UserWarning, match="could not write to cache"):
            result = engine.get("k", lambda: b"fetched")
        assert result == b"fetched"
        monkeypatch.undo()
        assert engine.peek("k") is None  # nothing was stored

    def test_rejects_a_decompression_bomb(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("pysmo.tools.cache._MAX_DECOMPRESSED_BYTES", 100)
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        bomb = zlib.compress(b"\x00" * 5000)
        engine._connect().execute(
            "INSERT INTO cache (key, data) VALUES ('bomb', ?)", (bomb,)
        )

        with pytest.raises(ValueError, match="decompresses to more than"):
            engine.peek("bomb")

    def test_rejects_a_truncated_blob(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        full = zlib.compress(b"payload" * 100)
        truncated = full[: len(full) // 2]
        engine._connect().execute(
            "INSERT INTO cache (key, data) VALUES ('cut', ?)", (truncated,)
        )
        with pytest.raises(ValueError, match="truncated zlib stream"):
            engine.peek("cut")

    def test_rejects_a_non_zlib_blob(self, tmp_path: Path) -> None:
        engine = BlobCache(path=tmp_path / "e.sqlite3", encoding_version=1)
        engine._connect().execute(
            "INSERT INTO cache (key, data) VALUES ('junk', ?)", (b"not zlib at all",)
        )
        with pytest.raises(ValueError, match="not valid zlib data"):
            engine.peek("junk")

    def test_read_only_session_persists_the_seeded_schema(self, tmp_path: Path) -> None:
        path = tmp_path / "e.sqlite3"
        reader = BlobCache(path=path, encoding_version=1)
        reader.peek("nothing-here")  # a hit-only session: never reaches _store
        reader.close()

        conn = sqlite3.connect(path)
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        conn.close()
        assert "cache" in names and "cache_stats" in names


class TestFetchCache:
    def test_miss_then_hit(
        self,
        cache: FetchCache,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        first = cache(station, starttime, endtime)
        second = cache(station, starttime, endtime)

        assert len(FETCH_CALLS) == 1
        assert list(first.data) == list(second.data) == [1.0, 2.0, 3.0]

    def test_distinct_station_and_window_both_fetched(
        self,
        cache: FetchCache,
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
        cache(station, starttime, endtime)
        cache(other_station, starttime, endtime)
        cache(station, starttime, endtime + pd.Timedelta(minutes=1))

        assert len(FETCH_CALLS) == 3

    def test_fetch_key_strips_nslc_padding(
        self, station: MiniStation, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> None:
        # SAC-style space-padded codes (past MiniStation's length validators,
        # hence a duck type) must key to the same row as the trimmed form.
        @define
        class PaddedStation:
            name: str
            network: str
            location: str
            channel: str
            latitude: float
            longitude: float
            elevation: float | None = None

        padded = PaddedStation(
            name=" ANMO ",
            network="IU ",
            location=" 00",
            channel="LHZ ",
            latitude=station.latitude,
            longitude=station.longitude,
        )
        assert _fetch_key(padded, starttime, endtime) == _fetch_key(
            station, starttime, endtime
        )

    def test_parse_runs_on_both_hit_and_miss(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        parse_calls: list[int] = []

        def counting_parse(raw: bytes) -> Seismogram:
            parse_calls.append(1)
            return fake_parse(raw)

        cache = FetchCache(
            path=tmp_path / "c.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=counting_parse,
        )
        cache(station, starttime, endtime)
        cache(station, starttime, endtime)
        # Parsing on the hit too is by design: the cache stores raw bytes.
        assert parse_calls == [1, 1]

    def test_parse_returning_sac_seismogram_works_every_call(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
        reference_event_assets: dict[str, Path],
    ) -> None:
        sac_bytes = reference_event_assets["sac_bhz"].read_bytes()

        def parse_sac(raw: bytes) -> Seismogram:
            return SAC.from_bytes(raw).seismogram

        cache = FetchCache(
            path=tmp_path / "c.sqlite3",
            fetch_raw=lambda **_: sac_bytes,
            parse=parse_sac,
        )
        first = cache(station, starttime, endtime)
        second = cache(station, starttime, endtime)
        assert type(first).__name__ == "SacSeismogram"
        assert (first.data == second.data).all()

    def test_reads_legacy_sqlite_archive_database(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        """A database written by the old SqliteArchiveFetcher is a drop-in."""
        path = tmp_path / "legacy.sqlite3"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE cache (key TEXT PRIMARY KEY, data BLOB NOT NULL)")
        conn.execute("PRAGMA user_version = 1")
        key = _fetch_key(station, starttime, endtime)
        conn.execute(
            "INSERT INTO cache (key, data) VALUES (?, ?)",
            (key, zlib.compress(RAW_BYTES)),
        )
        conn.commit()
        conn.close()

        cache = FetchCache(path=path, fetch_raw=fake_fetch_raw, parse=fake_parse)
        result = cache(station, starttime, endtime)
        assert len(FETCH_CALLS) == 0  # served from the legacy row
        assert list(result.data) == [1.0, 2.0, 3.0]

    def test_pickling_rebuilds_inner_engine(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        path = tmp_path / "c.sqlite3"
        cache = FetchCache(path=path, fetch_raw=fake_fetch_raw, parse=fake_parse)
        cache(station, starttime, endtime)
        assert cache._cache._conn is not None

        restored: FetchCache = pickle.loads(pickle.dumps(cache))
        assert restored._cache._conn is None

        result = restored(station, starttime, endtime)
        assert list(result.data) == [1.0, 2.0, 3.0]
        assert len(FETCH_CALLS) == 1  # the restored instance still hit the row

    def test_equality_ignores_connection_state(self, tmp_path: Path) -> None:
        path = tmp_path / "c.sqlite3"
        used = FetchCache(path=path, fetch_raw=fake_fetch_raw, parse=fake_parse)
        unused = FetchCache(path=path, fetch_raw=fake_fetch_raw, parse=fake_parse)
        used._cache._connect()

        assert used == unused

    def test_evicted_entry_refetched(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
    ) -> None:
        probe = FetchCache(
            path=tmp_path / "probe.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )
        probe(station, starttime, starttime + pd.Timedelta(minutes=1))
        one = (
            probe._cache._connect()
            .execute("SELECT COALESCE(SUM(length(data)), 0) FROM cache")
            .fetchone()[0]
        )
        probe.close()

        FETCH_CALLS.clear()
        cache = FetchCache(
            path=tmp_path / "c.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
            max_bytes=one,
        )
        t0, t1 = starttime, starttime + pd.Timedelta(minutes=1)
        t2, t3 = t1, starttime + pd.Timedelta(minutes=2)
        cache(station, t0, t1)  # fetch 1
        cache(station, t2, t3)  # fetch 2, evicts t0
        cache(station, t0, t1)  # fetch 3, t0 was evicted
        assert len(FETCH_CALLS) == 3

    def test_garbage_collection_closes_connection_without_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        cache = FetchCache(
            path=tmp_path / "c.sqlite3",
            fetch_raw=fake_fetch_raw,
            parse=fake_parse,
        )
        cache(station, starttime, endtime)

        unraisable: list[object] = []
        monkeypatch.setattr(sys, "unraisablehook", unraisable.append)
        del cache
        gc.collect()

        assert unraisable == []

    def test_missing_parent_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            FetchCache(
                path=tmp_path / "missing" / "c.sqlite3",
                fetch_raw=fake_fetch_raw,
                parse=fake_parse,
            )

    def test_empty_response_is_not_cached(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        responses = [b"", b"", RAW_BYTES]
        fetch_calls: list[int] = []

        def flaky_fetch(*, station: Station, **_: object) -> bytes:
            fetch_calls.append(1)
            return responses.pop(0)

        cache = FetchCache(
            path=tmp_path / "c.sqlite3", fetch_raw=flaky_fetch, parse=fake_parse
        )
        for _ in range(2):
            with pytest.raises(ValueError):  # fake_parse rejects b""
                cache(station, starttime, endtime)
        seismogram = cache(station, starttime, endtime)  # data now available
        assert list(seismogram.data) == [1.0, 2.0, 3.0]
        assert len(fetch_calls) == 3  # every call re-fetched; nothing stuck

    def test_unparseable_response_is_not_cached(
        self,
        tmp_path: Path,
        station: MiniStation,
        starttime: pd.Timestamp,
        endtime: pd.Timestamp,
    ) -> None:
        responses = [b"garbage", RAW_BYTES]

        def flaky_fetch(*, station: Station, **_: object) -> bytes:
            return responses.pop(0)

        cache = FetchCache(
            path=tmp_path / "c.sqlite3", fetch_raw=flaky_fetch, parse=fake_parse
        )
        with pytest.raises(ValueError):
            cache(station, starttime, endtime)
        seismogram = cache(station, starttime, endtime)
        assert list(seismogram.data) == [1.0, 2.0, 3.0]


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

    cache = FetchCache(
        path=tmp_path / "c.sqlite3",
        fetch_raw=fetch_mseed,
        parse=MSeed.from_bytes,
    )
    starttime = pd.Timestamp("2010-02-27T06:44:00Z")
    endtime = pd.Timestamp("2010-02-27T06:54:00Z")

    first = cache(station, starttime, endtime)
    second = cache(station, starttime, endtime)

    assert len(http_calls) == 1  # second call served from the cache
    assert isinstance(first, MSeed)
    assert (first.data == second.data).all()


@pytest.mark.real_web_request
def test_fetch_sac_pairing_live(tmp_path: Path, station: MiniStation) -> None:
    def parse_sac_zip(raw: bytes) -> Seismogram:
        return SAC.from_zip(raw).seismogram

    cache = FetchCache(
        path=tmp_path / "c.sqlite3", fetch_raw=fetch_sac, parse=parse_sac_zip
    )
    starttime = pd.Timestamp("2010-02-27T06:44:00Z")
    endtime = pd.Timestamp("2010-02-27T06:54:00Z")

    first = cache(station, starttime, endtime)
    second = cache(station, starttime, endtime)

    assert (first.data == second.data).all()
