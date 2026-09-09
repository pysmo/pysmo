"""Tests for pysmo.tools.project.TransformCache."""

import pickle
import warnings
import zlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from pysmo import MiniSeismogram, MiniStation, Seismogram, Station
from pysmo.classes import GeoCsvSeismogram
from pysmo.functions import clone_to_mini, seismogram_to_json
from pysmo.tools.iccs import MiniIccsSeismogram
from pysmo.tools.project import (
    FetchContext,
    ProjectEntry,
    PysmoProject,
    TransformCache,
)

type Ctx = FetchContext[Any, Any]
type Cache = TransformCache[Any, Any, Any]

TRANSFORM_CALLS: list[int] = []


def to_mini(seismogram: Seismogram, context: Ctx) -> MiniSeismogram:
    TRANSFORM_CALLS.append(1)
    return clone_to_mini(MiniSeismogram, seismogram)


def to_iccs(seismogram: Seismogram, context: Ctx) -> MiniIccsSeismogram:
    TRANSFORM_CALLS.append(1)
    return clone_to_mini(
        MiniIccsSeismogram, seismogram, update={"t0": context.reference}
    )


def to_geocsv(seismogram: Seismogram, context: Ctx) -> GeoCsvSeismogram:
    TRANSFORM_CALLS.append(1)
    return GeoCsvSeismogram(
        begin_time=seismogram.begin_time,
        delta=seismogram.delta,
        data=seismogram.data,
        sourceid="IU_ANMO_00_LHZ",
    )


def to_raw_seismogram(seismogram: Seismogram, context: Ctx) -> Seismogram:
    TRANSFORM_CALLS.append(1)
    return seismogram


def to_object(seismogram: Seismogram, context: Ctx) -> object:
    TRANSFORM_CALLS.append(1)
    return object()


def to_iccs_unserialisable_extra(
    seismogram: Seismogram, context: Ctx
) -> MiniIccsSeismogram:
    TRANSFORM_CALLS.append(1)
    result = clone_to_mini(
        MiniIccsSeismogram, seismogram, update={"t0": context.reference}
    )
    result.extra["thing"] = np.array([1.0, 2.0])
    return result


def to_iccs_lossy_extra(seismogram: Seismogram, context: Ctx) -> MiniIccsSeismogram:
    TRANSFORM_CALLS.append(1)
    result = clone_to_mini(
        MiniIccsSeismogram, seismogram, update={"t0": context.reference}
    )
    # A tuple survives JSON only as a list, so verify sees a changed value.
    result.extra["thing"] = (1, 2, 3)
    return result


@pytest.fixture(autouse=True)
def _reset_calls() -> None:
    TRANSFORM_CALLS.clear()


@pytest.fixture()
def station() -> MiniStation:
    return MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="BHZ",
        latitude=34.9459,
        longitude=-106.4571,
    )


@pytest.fixture()
def raw() -> MiniSeismogram:
    return MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:40:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0, 4.0]),
    )


@pytest.fixture()
def context(station: MiniStation) -> Ctx:
    entry: ProjectEntry[MiniStation, Any] = ProjectEntry(
        station=station,
        starttime=pd.Timestamp("2010-02-27T06:40:00Z"),
        endtime=pd.Timestamp("2010-02-27T06:50:00Z"),
    )
    return FetchContext(
        entry=entry,
        starttime=pd.Timestamp("2010-02-27T06:40:00Z"),
        endtime=pd.Timestamp("2010-02-27T06:50:00Z"),
        reference=pd.Timestamp("2010-02-27T06:44:00Z"),
    )


class TestCaching:
    def test_miss_then_hit(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_mini)
        first = cache(raw, context)
        second = cache(raw, context)

        assert len(TRANSFORM_CALLS) == 1
        assert first == second
        assert list(second.data) == [1.0, 2.0, 3.0, 4.0]

    @pytest.mark.parametrize(
        ("transform", "cls"),
        [
            (to_mini, MiniSeismogram),
            (to_iccs, MiniIccsSeismogram),
            (to_geocsv, GeoCsvSeismogram),
        ],
    )
    def test_round_trips_every_attrs_seismogram(
        self,
        tmp_path: Path,
        raw: MiniSeismogram,
        context: Ctx,
        transform: Any,
        cls: type,
    ) -> None:
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=transform)
        produced = cache(raw, context)
        reconstructed = cache(raw, context)

        assert type(produced) is cls
        assert type(reconstructed) is cls
        assert reconstructed == produced
        assert np.array_equal(reconstructed.data, raw.data)


class TestKey:
    def _entries_differ(
        self,
        cache: Cache,
        raw_a: Seismogram,
        ctx_a: Ctx,
        raw_b: Seismogram,
        ctx_b: Ctx,
    ) -> None:
        cache(raw_a, ctx_a)
        cache(raw_b, ctx_b)
        assert len(TRANSFORM_CALLS) == 2

    def test_reference_differs_at_identical_window_edges(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        assert context.reference is not None
        other = FetchContext(
            entry=context.entry,
            starttime=context.starttime,
            endtime=context.endtime,
            reference=context.reference + pd.Timedelta(seconds=5),
        )
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_iccs)
        self._entries_differ(cache, raw, context, raw, other)

    def test_resolved_window_differs(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        other = FetchContext(
            entry=context.entry,
            starttime=context.starttime,
            endtime=context.endtime + pd.Timedelta(minutes=1),
            reference=context.reference,
        )
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_mini)
        self._entries_differ(cache, raw, context, raw, other)

    def test_wrapped_transform_differs(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache_a = TransformCache(path=tmp_path / "t.sqlite3", transform=to_mini)
        cache_b = TransformCache(path=tmp_path / "t.sqlite3", transform=to_geocsv)
        cache_a(raw, context)
        cache_b(raw, context)
        assert len(TRANSFORM_CALLS) == 2

    def test_input_checksum_differs(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        other_raw = MiniSeismogram(
            begin_time=raw.begin_time,
            delta=raw.delta,
            data=raw.data + 1.0,
        )
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_mini)
        self._entries_differ(cache, raw, context, other_raw, context)


class TestGate:
    def test_non_attrs_result_raises(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_object)
        with pytest.raises(TypeError, match="clone_to_mini"):
            cache(raw, context)

    def test_sac_seismogram_result_raises(
        self,
        tmp_path: Path,
        context: Ctx,
        reference_event_assets: dict[str, Path],
    ) -> None:
        from pysmo.classes import SAC

        sac_seismogram = SAC.from_file(reference_event_assets["sac_bhz"]).seismogram
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_raw_seismogram)
        with pytest.raises(TypeError, match="clone_to_mini"):
            cache(sac_seismogram, context)


class TestCodec:
    def test_unserialisable_field_raises_typeerror(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache = TransformCache(
            path=tmp_path / "t.sqlite3", transform=to_iccs_unserialisable_extra
        )
        with pytest.raises(TypeError, match="clone_to_mini"):
            cache(raw, context)

    def test_lossy_value_caught_by_verify(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache = TransformCache(
            path=tmp_path / "t.sqlite3", transform=to_iccs_lossy_extra
        )
        with pytest.raises(TypeError, match="round trip"):
            cache(raw, context)

    def test_verify_false_skips_check(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache = TransformCache(
            path=tmp_path / "t.sqlite3", transform=to_mini, verify=False
        )
        assert cache(raw, context) == cache(raw, context)


class TestPysmoProjectIntegration:
    def test_checksum_still_recorded_on_transform_cache_hit(
        self, tmp_path: Path, station: MiniStation
    ) -> None:
        fetch_calls: list[int] = []

        def spy_fetch(s: Station, t0: pd.Timestamp, t1: pd.Timestamp) -> MiniSeismogram:
            fetch_calls.append(1)
            return MiniSeismogram(
                begin_time=t0, delta=pd.Timedelta(seconds=1), data=[1.0, 2.0, 3.0]
            )

        entry: ProjectEntry[MiniStation, Any] = ProjectEntry(
            station=station,
            starttime=pd.Timestamp("2020-01-01T00:00:00Z"),
            endtime=pd.Timestamp("2020-01-01T00:10:00Z"),
        )
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_mini)
        project = PysmoProject(
            entries=[entry],
            fetch_seismogram=spy_fetch,
            seismogram_transform=cache,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            project.get(entry.identity)
            project.clear_cache()  # force the second call past the in-memory cache
            project.get(entry.identity)

        assert fetch_calls == [1, 1]  # fetch still runs on the transform-cache hit
        assert entry.checksum is not None
        assert len(TRANSFORM_CALLS) == 1  # transform only ran on the first miss

    def test_resolution_context_digest_covers_wrapped_transform_not_storage(
        self, tmp_path: Path
    ) -> None:
        plain = PysmoProject(entries=[], seismogram_transform=to_mini)
        wrapped = PysmoProject(
            entries=[],
            seismogram_transform=TransformCache(
                path=tmp_path / "t.sqlite3", transform=to_mini
            ),
        )
        # Storage config (path, max_bytes, wal) does not change what a call
        # returns, so it is excluded from the wrapper's identity.
        relocated_and_capped = PysmoProject(
            entries=[],
            seismogram_transform=TransformCache(
                path=tmp_path / "elsewhere.sqlite3",
                transform=to_mini,
                max_bytes=1024,
                wal=True,
            ),
        )
        unverified = PysmoProject(
            entries=[],
            seismogram_transform=TransformCache(
                path=tmp_path / "t.sqlite3", transform=to_mini, verify=False
            ),
        )
        assert plain.resolution_context_digest != wrapped.resolution_context_digest
        assert (
            wrapped.resolution_context_digest
            == relocated_and_capped.resolution_context_digest
        )
        assert wrapped.resolution_context_digest != unverified.resolution_context_digest


class TestPickling:
    def test_used_cache_pickles_and_rebuilds_engine(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_mini)
        cache(raw, context)
        assert cache._cache._conn is not None

        restored: Cache = pickle.loads(pickle.dumps(cache))
        assert restored._cache._conn is None
        assert restored(raw, context) == cache(raw, context)
        assert len(TRANSFORM_CALLS) == 1  # both served from the file

    def test_racing_insert_or_ignore_does_not_raise(
        self, tmp_path: Path, raw: MiniSeismogram, context: Ctx
    ) -> None:
        cache = TransformCache(path=tmp_path / "t.sqlite3", transform=to_mini)
        blob = seismogram_to_json(to_mini(raw, context))
        conn = cache._cache._connect()
        for _ in range(2):
            with conn:
                conn.execute(
                    "INSERT OR IGNORE INTO cache (key, data) VALUES (?, ?)",
                    ("k", zlib.compress(blob)),
                )
        rows = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        assert rows == 1
