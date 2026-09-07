"""Tests for project entry identity and resolution context digest."""

import functools
import re
from pathlib import Path
from typing import Any

import attrs
import pandas as pd
import pytest

from pysmo import MiniEvent, MiniSeismogram, MiniStation, Seismogram, Station
from pysmo.tools.project import (
    FetchContext,
    PhaseWindow,
    ProjectEntry,
    PysmoProject,
    callable_identity,
    entry_identity,
    resolution_context_digest,
)
from pysmo.tools.traveltime import travel_times


def dummy_func(x: Any) -> Any:
    return x


def dummy_transform(seis: Seismogram, ctx: FetchContext[Any, Any]) -> Seismogram:
    return seis


def dummy_fetch(
    station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> Seismogram:
    return MiniSeismogram(begin_time=starttime, delta=pd.Timedelta(seconds=1), data=[])


def another_dummy_fetch(
    station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> Seismogram:
    return MiniSeismogram(begin_time=starttime, delta=pd.Timedelta(seconds=1), data=[])


type ProjectT = PysmoProject[MiniStation, MiniEvent, MiniSeismogram]


@attrs.define
class AttrsTransform:
    corner: float
    order: int = 4


@attrs.define
class AttrsFetcherWithPath:
    db_path: Path
    max_bytes: int | None = None

    def __call__(
        self, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> Seismogram:
        return MiniSeismogram(
            begin_time=starttime, delta=pd.Timedelta(seconds=1), data=[]
        )


@attrs.define
class DuckEvent:
    latitude: float
    longitude: float
    depth: float
    time: pd.Timestamp


@attrs.define
class DuckStation:
    name: str
    network: str
    location: str
    channel: str
    latitude: float
    longitude: float
    elevation: float | None = None


class TestEntryIdentity:
    def test_identical_natural_keys_produce_equal_identity(self) -> None:
        station1 = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        station2 = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        t = pd.Timestamp("2010-02-27T06:34:11.53Z")
        event1 = MiniEvent(latitude=-36.122, longitude=-72.898, depth=22900.0, time=t)
        event2 = MiniEvent(latitude=-36.122, longitude=-72.898, depth=22900.0, time=t)

        entry1 = ProjectEntry(station=station1, event=event1)
        entry2 = ProjectEntry(station=station2, event=event2)

        assert entry1.identity == entry2.identity
        assert entry1.identity_components == entry2.identity_components
        assert entry_identity(entry1) == entry1.identity

    def test_identity_format(self) -> None:
        station = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        event = MiniEvent(
            latitude=-36.122,
            longitude=-72.898,
            depth=22900.0,
            time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
        )
        entry = ProjectEntry(station=station, event=event)
        assert re.match(r"^v1:[0-9a-f]{64}$", entry.identity) is not None
        assert entry.identity.startswith("v1:")
        assert len(entry.identity) == 67

    def test_lat_lon_jitter_tolerance(self) -> None:
        station = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        t = pd.Timestamp("2010-02-27T06:34:11.53Z")
        base_event = MiniEvent(
            latitude=-36.1220, longitude=-72.8980, depth=22900.0, time=t
        )
        # Nudge within precision (< 5e-5 deg): rounds to same 4 decimal places
        nudged_event = MiniEvent(
            latitude=-36.12204, longitude=-72.89803, depth=22900.0, time=t
        )
        # Nudge beyond precision: changes 4th decimal place
        past_event = MiniEvent(
            latitude=-36.1221, longitude=-72.8980, depth=22900.0, time=t
        )

        base_entry = ProjectEntry(station=station, event=base_event)
        nudged_entry = ProjectEntry(station=station, event=nudged_event)
        past_entry = ProjectEntry(station=station, event=past_event)

        assert base_entry.identity == nudged_entry.identity
        assert base_entry.identity != past_entry.identity

    def test_depth_jitter_tolerance(self) -> None:
        station = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        t = pd.Timestamp("2010-02-27T06:34:11.53Z")
        base_event = MiniEvent(
            latitude=-36.1220, longitude=-72.8980, depth=10000.0, time=t
        )
        # Nudge within 50 m quantum: rounds to 10000.0
        nudged_event = MiniEvent(
            latitude=-36.1220, longitude=-72.8980, depth=10040.0, time=t
        )
        # Nudge past quantum: rounds to 10100.0
        past_event = MiniEvent(
            latitude=-36.1220, longitude=-72.8980, depth=10060.0, time=t
        )

        base_entry = ProjectEntry(station=station, event=base_event)
        nudged_entry = ProjectEntry(station=station, event=nudged_event)
        past_entry = ProjectEntry(station=station, event=past_event)

        assert base_entry.identity == nudged_entry.identity
        assert base_entry.identity != past_entry.identity

    def test_origin_time_nudged_by_one_nanosecond_changes_identity(self) -> None:
        station = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        t0 = pd.Timestamp("2010-02-27T06:34:11.530000000Z")
        t1 = pd.Timestamp("2010-02-27T06:34:11.530000001Z")
        event0 = MiniEvent(
            latitude=-36.1220, longitude=-72.8980, depth=22900.0, time=t0
        )
        event1 = MiniEvent(
            latitude=-36.1220, longitude=-72.8980, depth=22900.0, time=t1
        )

        entry0 = ProjectEntry(station=station, event=event0)
        entry1 = ProjectEntry(station=station, event=event1)

        assert entry0.identity != entry1.identity

    def test_station_location_canonicalisation(self) -> None:
        event = MiniEvent(
            latitude=-36.1220,
            longitude=-72.8980,
            depth=22900.0,
            time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
        )
        s_blank = DuckStation(
            name="ANMO",
            network="IU",
            location="",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        s_padded = DuckStation(
            name="ANMO",
            network="IU",
            location="  ",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        s_spaced_zero = DuckStation(
            name="ANMO",
            network="IU",
            location=" 0 ",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        s_zero_zero = DuckStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )

        e_blank = ProjectEntry(station=s_blank, event=event)
        e_padded = ProjectEntry(station=s_padded, event=event)
        e_spaced_zero = ProjectEntry(station=s_spaced_zero, event=event)
        e_zero_zero = ProjectEntry(station=s_zero_zero, event=event)

        assert e_blank.identity == e_padded.identity
        assert e_blank.identity_components["station"]["location"] == ""
        assert e_spaced_zero.identity_components["station"]["location"] == "0"
        assert e_zero_zero.identity != e_blank.identity
        assert e_zero_zero.identity != e_spaced_zero.identity

    def test_eventless_entry_with_explicit_window(self) -> None:
        station = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        t0 = pd.Timestamp("2020-01-01T00:00:00Z")
        t1 = pd.Timestamp("2020-01-01T01:00:00Z")
        t2 = pd.Timestamp("2020-01-01T02:00:00Z")

        entry1 = ProjectEntry(station=station, starttime=t0, endtime=t1)
        entry2 = ProjectEntry(station=station, starttime=t0, endtime=t2)

        assert entry1.identity_components["event"] is None
        assert entry1.identity_components["window"] == {
            "starttime_ns": t0.value,
            "endtime_ns": t1.value,
        }
        assert entry1.identity != entry2.identity

    def test_integer_coordinates_match_float_equivalents(self) -> None:
        station = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.9459,
            longitude=-106.4571,
        )
        t = pd.Timestamp("2020-01-01T00:00:00Z")
        float_event = MiniEvent(latitude=12.0, longitude=34.0, depth=10000.0, time=t)
        # A duck-typed Event exposing integer coordinates.
        int_event = DuckEvent(latitude=12, longitude=34, depth=10000, time=t)

        entry_float = ProjectEntry(station=station, event=float_event)
        entry_int = ProjectEntry(station=station, event=int_event)

        assert entry_float.identity == entry_int.identity

    def test_negative_zero_normalisation(self) -> None:
        station = MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=0.0,
            longitude=0.0,
        )
        t = pd.Timestamp("2020-01-01T00:00:00Z")
        event_neg = MiniEvent(latitude=-0.0, longitude=-0.0, depth=-0.0, time=t)
        event_pos = MiniEvent(latitude=0.0, longitude=0.0, depth=0.0, time=t)

        entry_neg = ProjectEntry(station=station, event=event_neg)
        entry_pos = ProjectEntry(station=station, event=event_pos)

        assert entry_neg.identity == entry_pos.identity
        assert entry_neg.identity_components["event"] == {
            "latitude": 0.0,
            "longitude": 0.0,
            "depth_m": 0.0,
            "time_ns": t.value,
        }


class TestCallableIdentity:
    def test_top_level_function(self) -> None:
        cid = callable_identity(dummy_func)
        assert cid == f"func:{dummy_func.__module__}:{dummy_func.__qualname__}"

    def test_functools_partial(self) -> None:
        p1 = functools.partial(travel_times, model="ak135")
        p2 = functools.partial(travel_times, model="ak135")
        p3 = functools.partial(travel_times, model="iasp91")

        cid1 = callable_identity(p1)
        cid2 = callable_identity(p2)
        cid3 = callable_identity(p3)

        assert cid1 == cid2
        assert cid1 != cid3
        assert cid1.startswith("partial:func:")
        assert "ak135" in cid1

    def test_attrs_instance(self) -> None:
        inst1 = AttrsTransform(corner=1.0, order=4)
        inst2 = AttrsTransform(corner=1.0, order=4)
        inst3 = AttrsTransform(corner=2.0, order=4)

        cid1 = callable_identity(inst1)
        cid2 = callable_identity(inst2)
        cid3 = callable_identity(inst3)

        assert cid1 == cid2
        assert cid1 != cid3
        assert cid1.startswith("attrs:")

    def test_attrs_instance_with_path_field(self) -> None:
        inst1 = AttrsFetcherWithPath(db_path=Path("/data/archive.sqlite"))
        inst2 = AttrsFetcherWithPath(db_path=Path("/data/archive.sqlite"))
        inst3 = AttrsFetcherWithPath(db_path=Path("/data/other.sqlite"))

        assert callable_identity(inst1) == callable_identity(inst2)
        assert callable_identity(inst1) != callable_identity(inst3)
        assert callable_identity(inst1).startswith("attrs:")

    def test_attrs_instance_with_nested_callable_field(self) -> None:
        # PhaseWindow holds `travel_time_backend` as a functools.partial,
        # which `_prepare_json_value` cannot reduce; the attrs branch must
        # recurse into it.
        base = PhaseWindow()
        assert callable_identity(base) == callable_identity(PhaseWindow())
        swapped = PhaseWindow(
            travel_time_backend=functools.partial(travel_times, model="ak135")
        )
        assert callable_identity(swapped) != callable_identity(base)
        assert callable_identity(base).startswith("attrs:")

    def test_unsupported_callables_raise_type_error(self) -> None:
        # Lambda
        with pytest.raises(TypeError, match="Closures and lambdas are not supported"):
            callable_identity(lambda x: x)

        # Local function / closure
        def local_fn() -> None:
            pass

        with pytest.raises(TypeError, match="Closures and lambdas are not supported"):
            callable_identity(local_fn)

        # Class itself
        with pytest.raises(TypeError, match="Classes are not supported"):
            callable_identity(AttrsTransform)

        # Bound method
        class Plain:
            def method(self) -> None:
                pass

        obj = Plain()
        with pytest.raises(TypeError, match="bound method"):
            callable_identity(obj.method)

        # Non-callable non-attrs
        with pytest.raises(TypeError, match="must be a top-level function"):
            callable_identity("not-a-callable")


class TestResolutionContextDigest:
    def test_format_and_stability(self) -> None:
        project: ProjectT = PysmoProject()
        digest = resolution_context_digest(project)
        assert re.match(r"^rc2:[0-9a-f]{64}$", digest) is not None
        assert digest.startswith("rc2:")
        assert len(digest) == 68

    def test_digest_changes_on_relevant_parameters(self) -> None:
        p1: ProjectT = PysmoProject(window=PhaseWindow(phase="P"))
        d1 = resolution_context_digest(p1)

        p2: ProjectT = PysmoProject(window=PhaseWindow(phase="S"))
        assert resolution_context_digest(p2) != d1

        p3: ProjectT = PysmoProject(
            window=PhaseWindow(pre_pick=pd.Timedelta(minutes=-3))
        )
        assert resolution_context_digest(p3) != d1

        p4: ProjectT = PysmoProject(
            window=PhaseWindow(post_pick=pd.Timedelta(minutes=10))
        )
        assert resolution_context_digest(p4) != d1

        p5: ProjectT = PysmoProject(
            window=PhaseWindow(
                travel_time_backend=functools.partial(travel_times, model="ak135")
            )
        )
        assert resolution_context_digest(p5) != d1

        p6: PysmoProject[MiniStation, MiniEvent, Seismogram] = PysmoProject(
            seismogram_transform=dummy_transform
        )
        assert resolution_context_digest(p6) != d1

    def test_digest_excludes_fetch_seismogram(self) -> None:
        p1: ProjectT = PysmoProject(fetch_seismogram=dummy_fetch)
        p2: ProjectT = PysmoProject(fetch_seismogram=another_dummy_fetch)
        assert resolution_context_digest(p1) == resolution_context_digest(p2)
