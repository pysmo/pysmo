"""Tests for WindowResult, PhaseWindow, and the explicit-window pre-check."""

import functools
import pickle
from collections.abc import Sequence

import attrs
import pandas as pd
import pytest

from pysmo import Event, MiniEvent, MiniSeismogram, MiniStation, Seismogram, Station
from pysmo.tools.project import (
    FetchContext,
    PhaseWindow,
    ProjectEntry,
    PysmoProject,
    WindowResult,
)
from pysmo.tools.traveltime import travel_times


def fake_travel_time_backend(
    *, depth: float, distance: float, phases: Sequence[str]
) -> dict[str, pd.Timedelta]:
    return {"P": pd.Timedelta(seconds=100.0), "S": pd.Timedelta(seconds=200.0)}


def no_arrival_travel_time_backend(
    *, depth: float, distance: float, phases: Sequence[str]
) -> dict[str, pd.Timedelta]:
    return {}


def fake_fetch_seismogram(
    station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> Seismogram:
    return MiniSeismogram(
        begin_time=starttime, delta=pd.Timedelta(seconds=1), data=[1.0, 2.0, 3.0]
    )


def identity_transform[TStation: Station, TEvent: Event](
    seismogram: Seismogram, context: FetchContext[TStation, TEvent]
) -> Seismogram:
    return seismogram


class TestWindowResult:
    def test_construction_and_frozen(self) -> None:
        t0 = pd.Timestamp("2020-01-01T00:00:00Z")
        t1 = pd.Timestamp("2020-01-01T00:10:00Z")
        result = WindowResult(starttime=t0, endtime=t1, reference=None)
        assert result.starttime == t0
        assert result.endtime == t1
        assert result.reference is None
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            result.starttime = t1  # type: ignore[misc]


class TestPhaseWindow:
    def test_window_derived_from_event(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        window = PhaseWindow(travel_time_backend=fake_travel_time_backend)
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        result = window(entry)

        expected_reference = event_maule.time + pd.Timedelta(seconds=100.0)
        assert result.reference == expected_reference
        assert result.starttime == expected_reference + window.pre_pick
        assert result.endtime == expected_reference + window.post_pick

    def test_custom_phase(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        window = PhaseWindow(phase="S", travel_time_backend=fake_travel_time_backend)
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        result = window(entry)
        assert result.reference == event_maule.time + pd.Timedelta(seconds=200.0)

    def test_eventless_entry_raises(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        entry.event = None
        window = PhaseWindow(travel_time_backend=fake_travel_time_backend)
        with pytest.raises(ValueError, match="needs an entry with an event"):
            window(entry)

    def test_no_predicted_arrival_raises(
        self, station_anmo: MiniStation, event_maule: MiniEvent
    ) -> None:
        window = PhaseWindow(travel_time_backend=no_arrival_travel_time_backend)
        entry = ProjectEntry(station=station_anmo, event=event_maule)
        with pytest.raises(ValueError, match="No 'P' arrival predicted"):
            window(entry)

    def test_equality_and_pickle_round_trip(self) -> None:
        # Equal when the backend compares equal (a plain function does; the
        # default `functools.partial` does not, hence the explicit backend).
        assert PhaseWindow(travel_time_backend=fake_travel_time_backend) == PhaseWindow(
            travel_time_backend=fake_travel_time_backend
        )
        restored = pickle.loads(pickle.dumps(PhaseWindow(phase="S")))
        assert restored.phase == "S"
        assert restored.pre_pick == PhaseWindow().pre_pick
        assert isinstance(restored.travel_time_backend, functools.partial)
        assert restored.travel_time_backend.func is travel_times


class TestPhaseWindowValidators:
    def test_pre_pick_zero_is_valid(self) -> None:
        PhaseWindow(pre_pick=pd.Timedelta(0))

    def test_pre_pick_positive_raises(self) -> None:
        with pytest.raises(ValueError):
            PhaseWindow(pre_pick=pd.Timedelta(seconds=1))

    def test_post_pick_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            PhaseWindow(post_pick=pd.Timedelta(0))

    def test_post_pick_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            PhaseWindow(post_pick=pd.Timedelta(seconds=-1))


class TestExplicitWindowPreCheck:
    def test_explicit_window_bypasses_the_resolver(
        self, station_anmo: MiniStation
    ) -> None:
        calls: list[ProjectEntry[MiniStation, MiniEvent]] = []

        def spy_window(entry: ProjectEntry[MiniStation, MiniEvent]) -> WindowResult:
            calls.append(entry)
            raise AssertionError("resolver should not be called")

        t0 = pd.Timestamp("2020-01-01T00:00:00Z")
        t1 = pd.Timestamp("2020-01-01T00:10:00Z")
        entry = ProjectEntry[MiniStation, MiniEvent](
            station=station_anmo, starttime=t0, endtime=t1
        )
        captured: list[FetchContext[MiniStation, MiniEvent]] = []

        def capture_transform(
            seismogram: Seismogram, context: FetchContext[MiniStation, MiniEvent]
        ) -> Seismogram:
            captured.append(context)
            return seismogram

        project: PysmoProject[MiniStation, MiniEvent, Seismogram] = PysmoProject(
            entries=[entry],
            seismogram_transform=capture_transform,
            fetch_seismogram=fake_fetch_seismogram,
            window=spy_window,
        )
        project._fetch(entry)

        assert calls == []
        assert captured[0].starttime == t0
        assert captured[0].endtime == t1
        assert captured[0].reference is None
