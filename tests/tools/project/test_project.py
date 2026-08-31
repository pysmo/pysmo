"""Tests for pysmo.tools.project."""

import pickle
import sys
import threading
import time
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import pandas as pd
import pytest

from pysmo import Event, MiniEvent, MiniSeismogram, MiniStation, Seismogram, Station
from pysmo.tools.project import (
    FetchContext,
    ProjectEntry,
    PysmoProject,
    build_entries,
)

# `identity_transform` returns the bare `Seismogram` protocol, so a project
# built with it in these tests is parameterised on `Seismogram`, not the
# `MiniSeismogram` default.
type ProjectT = PysmoProject[MiniStation, MiniEvent, Seismogram]

FETCH_CALLS: list[tuple[str, pd.Timestamp, pd.Timestamp]] = []
FETCH_DATA_OVERRIDE: dict[str, list[float]] = {}


def fake_fetch_seismogram(
    station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> Seismogram:
    """Module-level (not a closure) stand-in for a real network fetch."""
    FETCH_CALLS.append((station.name, starttime, endtime))
    data = FETCH_DATA_OVERRIDE.get(station.name, [1.0, 2.0, 3.0])
    return MiniSeismogram(
        begin_time=starttime, delta=pd.Timedelta(seconds=1), data=list(data)
    )


def other_fake_fetch_seismogram(
    station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> Seismogram:
    """A second, distinct top-level fetch function for swap tests."""
    return fake_fetch_seismogram(station, starttime, endtime)


def identity_transform[TStation: Station, TEvent: Event](
    seismogram: Seismogram, context: FetchContext[TStation, TEvent]
) -> Seismogram:
    """Module-level (not a closure) transform returning the seismogram unchanged."""
    return seismogram


def other_identity_transform[TStation: Station, TEvent: Event](
    seismogram: Seismogram, context: FetchContext[TStation, TEvent]
) -> Seismogram:
    """A second, distinct top-level transform function for swap tests."""
    return seismogram


def fake_travel_time_backend(
    *, depth: float, distance: float, phases: Sequence[str]
) -> dict[str, pd.Timedelta]:
    return {"P": pd.Timedelta(seconds=100.0), "S": pd.Timedelta(seconds=200.0)}


def other_travel_time_backend(
    *, depth: float, distance: float, phases: Sequence[str]
) -> dict[str, pd.Timedelta]:
    return {"P": pd.Timedelta(seconds=300.0), "S": pd.Timedelta(seconds=400.0)}


def no_arrival_travel_time_backend(
    *, depth: float, distance: float, phases: Sequence[str]
) -> dict[str, pd.Timedelta]:
    """Stands in for a geometry with no predicted arrival for the requested phase."""
    return {}


@pytest.fixture(autouse=True)
def _reset_fetch_state() -> None:
    FETCH_CALLS.clear()
    FETCH_DATA_OVERRIDE.clear()


@pytest.fixture()
def project(station_anmo: MiniStation, event_maule: MiniEvent) -> ProjectT:
    return PysmoProject(
        entries=[ProjectEntry(station=station_anmo, event=event_maule)],
        seismogram_transform=identity_transform,
        fetch_seismogram=fake_fetch_seismogram,
        travel_time_backend=fake_travel_time_backend,
    )


class TestProjectEntry:
    def test_defaults(self, station_anmo: MiniStation) -> None:
        entry = ProjectEntry(station=station_anmo)
        assert entry.event is None
        assert entry.starttime is None
        assert entry.endtime is None
        assert entry.checksum is None

    def test_string_and_datetime_converted_to_utc_timestamp(
        self, station_anmo: MiniStation
    ) -> None:
        entry = ProjectEntry(
            station=station_anmo,
            starttime="2024-01-01T00:00:00",
            endtime="2024-01-01T00:01:00",
        )
        assert entry.starttime == pd.Timestamp("2024-01-01T00:00:00Z")
        assert entry.endtime == pd.Timestamp("2024-01-01T00:01:00Z")
        assert entry.starttime.tz is not None


class TestResolveWindow:
    def test_explicit_window_wins_over_event(
        self,
        project: ProjectT,
        station_anmo: MiniStation,
        event_maule: MiniEvent,
    ) -> None:
        explicit_start = pd.Timestamp("2020-01-01T00:00:00Z")
        explicit_end = pd.Timestamp("2020-01-01T00:01:00Z")
        entry = ProjectEntry(
            station=station_anmo,
            event=event_maule,
            starttime=explicit_start,
            endtime=explicit_end,
        )
        starttime, endtime, predicted = project._resolve_window(entry)
        assert (starttime, endtime, predicted) == (explicit_start, explicit_end, None)

    def test_window_derived_from_event(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        starttime, endtime, predicted = project._resolve_window(entry)

        expected_predicted = event_maule.time + pd.Timedelta(seconds=100.0)
        assert predicted == expected_predicted
        assert starttime == expected_predicted + project.pre_pick
        assert endtime == expected_predicted + project.post_pick

    def test_neither_window_nor_event_raises(
        self, project: ProjectT, station_anmo: MiniStation
    ) -> None:
        entry: ProjectEntry[MiniStation, MiniEvent] = ProjectEntry(station=station_anmo)
        with pytest.raises(ValueError, match="explicit window or an event"):
            project._resolve_window(entry)

    def test_no_predicted_arrival_for_phase_raises_value_error(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project: ProjectT = PysmoProject(
            entries=[],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=no_arrival_travel_time_backend,
        )
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        with pytest.raises(ValueError, match="No 'P' arrival predicted"):
            project._resolve_window(entry)


class TestPickPickValidators:
    def test_pre_pick_zero_is_valid(self) -> None:
        PysmoProject(seismogram_transform=identity_transform, pre_pick=pd.Timedelta(0))

    def test_pre_pick_positive_raises(self) -> None:
        with pytest.raises(ValueError):
            PysmoProject(
                seismogram_transform=identity_transform,
                pre_pick=pd.Timedelta(seconds=1),
            )

    def test_post_pick_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            PysmoProject(
                seismogram_transform=identity_transform, post_pick=pd.Timedelta(0)
            )

    def test_post_pick_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            PysmoProject(
                seismogram_transform=identity_transform,
                post_pick=pd.Timedelta(seconds=-1),
            )


class TestQuerySurface:
    def test_stations_and_events_distinct_first_seen(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
        event_other: MiniEvent,
    ) -> None:
        project = PysmoProject(
            entries=[
                ProjectEntry(station=station_anmo, event=event_maule),
                ProjectEntry(station=station_cacb, event=event_maule),
                ProjectEntry(station=station_anmo, event=event_other),
            ],
            seismogram_transform=identity_transform,
        )
        assert project.stations == [station_anmo, station_cacb]
        assert project.events == [event_maule, event_other]

    def test_events_excludes_eventless_entries(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project = PysmoProject(
            entries=[
                ProjectEntry(station=station_anmo, event=event_maule),
                ProjectEntry[MiniStation, MiniEvent](
                    station=station_anmo,
                    starttime="2024-01-01T00:00:00Z",
                    endtime="2024-01-01T00:01:00Z",
                ),
            ],
            seismogram_transform=identity_transform,
        )
        assert project.events == [event_maule]

    def test_events_for_includes_none_for_eventless_entry(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project = PysmoProject(
            entries=[
                ProjectEntry(station=station_anmo, event=event_maule),
                ProjectEntry[MiniStation, MiniEvent](
                    station=station_anmo,
                    starttime="2024-01-01T00:00:00Z",
                    endtime="2024-01-01T00:01:00Z",
                ),
            ],
            seismogram_transform=identity_transform,
        )
        assert project.events_for(station_anmo) == [event_maule, None]

    def test_stations_for_none_returns_eventless_stations(
        self, station_anmo: MiniStation
    ) -> None:
        project = PysmoProject(
            entries=[
                ProjectEntry[MiniStation, MiniEvent](
                    station=station_anmo,
                    starttime="2024-01-01T00:00:00Z",
                    endtime="2024-01-01T00:01:00Z",
                ),
            ],
            seismogram_transform=identity_transform,
        )
        assert project.stations_for(None) == [station_anmo]


class TestFetchAll:
    def test_fetches_every_entry_including_eventless(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
    ) -> None:
        project = PysmoProject(
            entries=[
                ProjectEntry(station=station_anmo, event=event_maule),
                ProjectEntry[MiniStation, MiniEvent](
                    station=station_cacb,
                    starttime="2024-01-01T00:00:00Z",
                    endtime="2024-01-01T00:01:00Z",
                ),
            ],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        results = project.fetch_all()
        assert len(results) == 2
        assert len(FETCH_CALLS) == 2
        assert FETCH_CALLS[0][0] == "ANMO"
        assert FETCH_CALLS[1][0] == "CACB"


class TestSeismogramCaching:
    def test_repeated_call_uses_cache(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 1

    def test_distinct_entries_produce_distinct_cache_entries(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        other_channel_station = MiniStation(
            name=station_anmo.name,
            network=station_anmo.network,
            location=station_anmo.location,
            channel="LHN",
            latitude=station_anmo.latitude,
            longitude=station_anmo.longitude,
        )
        project = PysmoProject(
            entries=[
                ProjectEntry(station=station_anmo, event=event_maule),
                ProjectEntry(station=other_channel_station, event=event_maule),
            ],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        project.seismogram(station_anmo, event_maule)
        project.seismogram(other_channel_station, event_maule)
        assert len(FETCH_CALLS) == 2

    def test_event_derived_and_explicit_window_entries_not_merged(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        predicted = event_maule.time + pd.Timedelta(seconds=100.0)
        explicit_start = predicted + pd.Timedelta(minutes=-2)
        explicit_end = predicted + pd.Timedelta(minutes=8)

        event_entry = ProjectEntry(station=station_anmo, event=event_maule)
        explicit_entry = ProjectEntry[MiniStation, MiniEvent](
            station=station_anmo, starttime=explicit_start, endtime=explicit_end
        )
        project = PysmoProject(
            entries=[event_entry, explicit_entry],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        project._fetch(event_entry)
        project._fetch(explicit_entry)
        assert len(FETCH_CALLS) == 2


class TestSeismogramErrors:
    def test_no_match_raises_key_error(
        self, project: ProjectT, station_cacb: MiniStation
    ) -> None:
        with pytest.raises(KeyError):
            project.seismogram(station_cacb)

    def test_duplicate_match_raises_value_error(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project = PysmoProject(
            entries=[
                ProjectEntry(
                    station=station_anmo,
                    event=event_maule,
                    starttime="2024-01-01T00:00:00Z",
                    endtime="2024-01-01T00:01:00Z",
                ),
                ProjectEntry(
                    station=station_anmo,
                    event=event_maule,
                    starttime="2024-06-01T00:00:00Z",
                    endtime="2024-06-01T00:01:00Z",
                ),
            ],
            seismogram_transform=identity_transform,
        )
        with pytest.raises(ValueError, match="More than one entry"):
            project.seismogram(station_anmo, event_maule)


class TestCacheInvalidation:
    def test_phase_change_triggers_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.phase = "S"
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2
        assert FETCH_CALLS[0][1] != FETCH_CALLS[1][1]

    def test_pre_pick_change_triggers_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.pre_pick = pd.Timedelta(minutes=-1)
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2

    def test_post_pick_change_triggers_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.post_pick = pd.Timedelta(minutes=9)
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2

    def test_travel_time_backend_change_triggers_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.travel_time_backend = other_travel_time_backend
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2
        assert FETCH_CALLS[0][1] != FETCH_CALLS[1][1]

    def test_fetch_seismogram_change_triggers_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.fetch_seismogram = other_fake_fetch_seismogram
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2

    def test_transform_change_triggers_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.seismogram_transform = other_identity_transform
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2

    def test_unrelated_reassignment_of_same_value_does_not_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        project.phase = "P"  # same value it already was
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 1

    def test_equal_but_distinct_object_does_not_refetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project.seismogram(station_anmo, event_maule)
        # A different Timedelta object with an equal value -- exercises the
        # `==` branch, not the `is` identity short-circuit.
        assert project.pre_pick == pd.Timedelta(seconds=-120)
        assert project.pre_pick is not pd.Timedelta(seconds=-120)
        project.pre_pick = pd.Timedelta(seconds=-120)
        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 1

    def test_clear_cache_bumps_generation(self, project: ProjectT) -> None:
        assert project._cache_generation == 0
        project.clear_cache()
        project.clear_cache()
        assert project._cache_generation == 2


class TestSeismogramsFor:
    def test_one_result_per_station_in_order(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
    ) -> None:
        project = PysmoProject(
            entries=[
                ProjectEntry(station=station_cacb, event=event_maule),
                ProjectEntry(station=station_anmo, event=event_maule),
            ],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        results = project.seismograms_for(event_maule)
        assert len(results) == 2
        assert FETCH_CALLS[0][0] == "CACB"
        assert FETCH_CALLS[1][0] == "ANMO"

    def test_no_matching_entries_returns_empty(
        self, project: ProjectT, event_other: MiniEvent
    ) -> None:
        assert project.seismograms_for(event_other) == []


class TestPickling:
    def test_cache_empty_after_round_trip_but_entries_survive(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project = PysmoProject(
            entries=[ProjectEntry(station=station_anmo, event=event_maule)],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        project.seismogram(station_anmo, event_maule)
        assert len(project._cache) == 1

        project.clear_cache()
        assert project._cache_generation == 1

        restored: ProjectT = pickle.loads(pickle.dumps(project))
        assert len(restored._cache) == 0
        assert restored._cache_generation == 0
        assert isinstance(restored._lock, type(threading.Lock()))

        restored.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2

    def test_equality_ignores_cache_state(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        entries = [ProjectEntry(station=station_anmo, event=event_maule)]
        used = PysmoProject(
            entries=entries,
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        unused = PysmoProject(
            entries=entries,
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        used.seismogram(station_anmo, event_maule)  # populates used._cache only

        assert used == unused


class TestThreadSafety:
    def test_concurrent_calls_converge_on_one_cached_result(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        def slow_fetch_seismogram(
            station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
        ) -> Seismogram:
            time.sleep(0.01)  # widen the race window between threads
            return fake_fetch_seismogram(station, starttime, endtime)

        project = PysmoProject(
            entries=[ProjectEntry(station=station_anmo, event=event_maule)],
            seismogram_transform=identity_transform,
            fetch_seismogram=slow_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        results: list[Seismogram] = []
        results_lock = threading.Lock()

        def worker() -> None:
            result = project.seismogram(station_anmo, event_maule)
            with results_lock:
                results.append(result)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(results) == 8
        assert all(result is results[0] for result in results)
        assert len(project._cache) == 1

    def test_parameter_change_mid_fetch_returns_result_uncached(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        fetch_started = threading.Event()
        may_finish = threading.Event()

        def blocking_fetch(
            station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
        ) -> Seismogram:
            fetch_started.set()
            may_finish.wait(timeout=5)
            return fake_fetch_seismogram(station, starttime, endtime)

        project = PysmoProject(
            entries=[ProjectEntry(station=station_anmo, event=event_maule)],
            seismogram_transform=identity_transform,
            fetch_seismogram=blocking_fetch,
            travel_time_backend=fake_travel_time_backend,
        )
        results: list[Seismogram] = []

        def worker() -> None:
            results.append(project.seismogram(station_anmo, event_maule))

        thread = threading.Thread(target=worker)
        thread.start()
        assert fetch_started.wait(timeout=5)
        project.phase = "S"  # clears the cache and bumps the generation
        may_finish.set()
        thread.join(timeout=5)

        assert len(results) == 1  # the in-flight fetch still returned a result
        assert project._cache == {}  # but it was not cached under the stale key

        project.seismogram(station_anmo, event_maule)
        assert len(FETCH_CALLS) == 2  # so the next call re-fetches


class TestChecksum:
    def test_checksum_set_on_first_fetch(
        self, project: ProjectT, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        entry = project.entries[0]
        assert entry.checksum is None
        project.seismogram(station_anmo, event_maule)
        assert entry.checksum is not None
        assert entry.checksum.startswith("sha256:")

    def test_checksum_survives_pickling_but_cache_does_not(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project = PysmoProject(
            entries=[ProjectEntry(station=station_anmo, event=event_maule)],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        project.seismogram(station_anmo, event_maule)
        original_checksum = project.entries[0].checksum

        restored: ProjectT = pickle.loads(pickle.dumps(project))
        assert restored.entries[0].checksum == original_checksum
        assert len(restored._cache) == 0

    @pytest.mark.parametrize("policy", ["warn", "raise", "ignore"])
    def test_mismatch_policy(
        self,
        policy: Literal["warn", "raise", "ignore"],
        station_anmo: MiniStation,
        event_maule: MiniEvent,
    ) -> None:
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        project = PysmoProject(
            entries=[entry],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
            on_checksum_mismatch=policy,
        )
        project.seismogram(station_anmo, event_maule)
        original_checksum = entry.checksum

        FETCH_DATA_OVERRIDE[station_anmo.name] = [9.0, 9.0, 9.0]
        project.clear_cache()

        if policy == "warn":
            with pytest.warns(UserWarning, match="no longer matches"):
                project.seismogram(station_anmo, event_maule)
        elif policy == "raise":
            with pytest.raises(ValueError, match="no longer matches"):
                project.seismogram(station_anmo, event_maule)
        else:
            project.seismogram(station_anmo, event_maule)

        assert entry.checksum == original_checksum

    def test_warning_stacklevel_points_at_seismogram_caller(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        project = PysmoProject(
            entries=[entry],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        project.seismogram(station_anmo, event_maule)
        FETCH_DATA_OVERRIDE[station_anmo.name] = [9.0, 9.0, 9.0]
        project.clear_cache()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            project.seismogram(station_anmo, event_maule)
            call_lineno = sys._getframe().f_lineno - 1
        assert caught[0].filename == __file__
        assert caught[0].lineno == call_lineno

    def test_warning_stacklevel_points_at_seismograms_for_caller(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        project = PysmoProject(
            entries=[entry],
            seismogram_transform=identity_transform,
            fetch_seismogram=fake_fetch_seismogram,
            travel_time_backend=fake_travel_time_backend,
        )
        project.seismogram(station_anmo, event_maule)
        FETCH_DATA_OVERRIDE[station_anmo.name] = [9.0, 9.0, 9.0]
        project.clear_cache()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            project.seismograms_for(event_maule)
            call_lineno = sys._getframe().f_lineno - 1
        assert caught[0].filename == __file__
        assert caught[0].lineno == call_lineno


def test_default_fetch_seismogram_uses_miniseed(
    monkeypatch: pytest.MonkeyPatch,
    station_anmo: MiniStation,
    event_maule: MiniEvent,
    reference_event_assets: dict[str, Path],
) -> None:
    fields_seen: dict[str, object] = {}

    def fake_http_get(url: str, fields: dict[str, object], **kwargs: object) -> bytes:
        fields_seen.update(fields)
        return reference_event_assets["mseed_bhz"].read_bytes()

    monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

    project = PysmoProject(
        entries=[ProjectEntry(station=station_anmo, event=event_maule)],
        travel_time_backend=fake_travel_time_backend,
    )
    seismogram = project.seismogram(station_anmo, event_maule)

    assert fields_seen["format"] == "miniseed"
    assert isinstance(seismogram, MiniSeismogram)
    assert len(seismogram.data) > 0


@pytest.mark.real_web_request
def test_default_fetch_seismogram_live(
    station_anmo: MiniStation, event_maule: MiniEvent
) -> None:
    project = PysmoProject(
        entries=[ProjectEntry(station=station_anmo, event=event_maule)],
        seismogram_transform=identity_transform,
    )
    seismogram = project.seismogram(station_anmo, event_maule)
    assert len(seismogram.data) > 0


class TestBuildEntries:
    def test_full_cross_product_when_no_predicate(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
        event_other: MiniEvent,
    ) -> None:
        entries = build_entries(
            [station_anmo, station_cacb], [event_maule, event_other]
        )
        assert len(entries) == 4
        # stations-outer, events-inner
        assert [(e.station, e.event) for e in entries] == [
            (station_anmo, event_maule),
            (station_anmo, event_other),
            (station_cacb, event_maule),
            (station_cacb, event_other),
        ]

    def test_predicate_filters_pairs(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
    ) -> None:
        entries = build_entries(
            [station_anmo, station_cacb],
            [event_maule],
            lambda s, e: s.network == "IU",
        )
        assert [e.station for e in entries] == [station_anmo]

    def test_empty_inputs(self, station_anmo: MiniStation) -> None:
        assert build_entries([station_anmo], []) == []

    def test_accepts_generators(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        entries = build_entries((s for s in [station_anmo]), (e for e in [event_maule]))
        assert len(entries) == 1

    def test_project_from_build_entries(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        project = PysmoProject(
            entries=build_entries([station_anmo], [event_maule]),
            seismogram_transform=identity_transform,
        )
        assert project.events == [event_maule]
        assert project.stations == [station_anmo]

    def test_incremental_growth_keeps_warm_cache(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
    ) -> None:
        project = PysmoProject(
            entries=build_entries([station_anmo], [event_maule]),
            fetch_seismogram=fake_fetch_seismogram,
            seismogram_transform=identity_transform,
            travel_time_backend=fake_travel_time_backend,
        )
        first = project.seismogram(station_anmo, event_maule)

        project.entries.extend(build_entries([station_cacb], [event_maule]))

        assert project.seismogram(station_anmo, event_maule) is first
        second = project.seismogram(station_cacb, event_maule)
        assert second is not first

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda entries, extra: entries.append(extra),
            lambda entries, extra: entries.extend([extra]),
            lambda entries, extra: entries.insert(0, extra),
            lambda entries, extra: entries.__setitem__(
                slice(1, 1), [extra]
            ),  # splice, keep both originals
            lambda entries, extra: entries.reverse(),
            lambda entries, extra: entries.sort(key=lambda e: e.station.name),
        ],
    )
    def test_in_place_entries_mutation_never_stales_the_cache(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
        mutate: "object",
    ) -> None:
        project = PysmoProject(
            entries=build_entries([station_anmo, station_cacb], [event_maule]),
            fetch_seismogram=fake_fetch_seismogram,
            seismogram_transform=identity_transform,
            travel_time_backend=fake_travel_time_backend,
        )
        anmo_result = project.seismogram(station_anmo, event_maule)
        cacb_result = project.seismogram(station_cacb, event_maule)
        FETCH_CALLS.clear()

        # a fresh, non-colliding entry (event-less window on ANMO)
        extra = ProjectEntry[MiniStation, MiniEvent](
            station=station_anmo,
            starttime="2024-01-01T00:00:00Z",
            endtime="2024-01-01T00:01:00Z",
        )
        mutate(project.entries, extra)  # type: ignore[operator]

        # every entry still present resolves from cache, no re-fetch
        assert project.seismogram(station_anmo, event_maule) is anmo_result
        assert project.seismogram(station_cacb, event_maule) is cacb_result
        assert FETCH_CALLS == []

    def test_removing_an_entry_orphans_its_cached_result(
        self,
        station_anmo: MiniStation,
        station_cacb: MiniStation,
        event_maule: MiniEvent,
    ) -> None:
        project = PysmoProject(
            entries=build_entries([station_anmo, station_cacb], [event_maule]),
            fetch_seismogram=fake_fetch_seismogram,
            seismogram_transform=identity_transform,
            travel_time_backend=fake_travel_time_backend,
        )
        project.fetch_all()

        del project.entries[0]  # drop the ANMO entry

        with pytest.raises(KeyError):
            project.seismogram(station_anmo, event_maule)
        # the surviving entry is untouched
        assert project.seismogram(station_cacb, event_maule) is not None


def _mini_seismogram_transform[TStation: Station, TEvent: Event](
    seismogram: Seismogram, context: FetchContext[TStation, TEvent]
) -> MiniSeismogram:
    return MiniSeismogram(
        begin_time=seismogram.begin_time,
        delta=seismogram.delta,
        data=seismogram.data,
    )


def _static_typing_checks(events: list[MiniEvent], stations: list[MiniStation]) -> None:
    """Compile-time only (pytest-mypy): generic parameters infer from construction.

    Never called — mypy fails the run if any assignment below widens. No
    annotations on `entries` / `project`: inference alone must produce the
    concrete parameters, including `TSeismogram` from the default transform.
    """
    entries = build_entries(stations, events)
    entries_typed: list[ProjectEntry[MiniStation, MiniEvent]] = entries

    project = PysmoProject(entries=entries)
    project_typed: PysmoProject[MiniStation, MiniEvent, MiniSeismogram] = project

    narrowed_events: list[MiniEvent] = project.events
    narrowed_stations: list[MiniStation] = project.stations
    fetched: list[MiniSeismogram] = project.seismograms_for(events[0])
    custom = PysmoProject(
        entries=entries, seismogram_transform=_mini_seismogram_transform
    )
    custom_typed: PysmoProject[MiniStation, MiniEvent, MiniSeismogram] = custom
    _ = (
        entries_typed,
        project_typed,
        narrowed_events,
        narrowed_stations,
        fetched,
        custom_typed,
    )
