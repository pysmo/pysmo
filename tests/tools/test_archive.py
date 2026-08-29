"""Tests for pysmo.tools.archive."""

import pickle
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from pysmo import MiniSeismogram, MiniStation, Seismogram, Station
from pysmo.classes import SAC
from pysmo.tools.archive import SqliteArchiveFetcher
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
