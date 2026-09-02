"""Tests for pysmo.classes.QuakeML."""

from pathlib import Path

import pandas as pd
import pytest

from pysmo import MiniEvent
from pysmo.classes import QuakeML
from pysmo.functions import clone_to_mini

_HEADER = (
    '<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2" '
    'xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">'
)

_ORIGIN = (
    '<origin publicID="smi:o/1">'
    "<time><value>2010-02-27T06:34:11.53Z</value></time>"
    "<latitude><value>-36.122</value></latitude>"
    "<longitude><value>-72.898</value></longitude>"
    "<depth><value>22900</value></depth>"
    "</origin>"
)


def _doc(*events: str) -> bytes:
    body = "\n".join(events)
    return (
        f'<?xml version="1.0"?>\n{_HEADER}\n'
        f'<eventParameters publicID="smi:c">\n{body}\n</eventParameters>\n</q:quakeml>'
    ).encode()


def _event(public_id: str, *, extra: str = "") -> str:
    return (
        f'<event publicID="{public_id}">{_ORIGIN}'
        f"<preferredOriginID>smi:o/1</preferredOriginID>{extra}</event>"
    )


class TestConformance:
    def test_clone_to_mini(self) -> None:
        event = QuakeML.from_bytes(_doc(_event("smi:e/1")))
        mini = clone_to_mini(MiniEvent, event)
        assert isinstance(mini, MiniEvent)
        assert mini.time == event.time
        assert mini.latitude == event.latitude
        assert mini.longitude == event.longitude
        assert mini.depth == event.depth


class TestReferenceFixture:
    @pytest.fixture()
    def maule(self, reference_event_assets: dict[str, Path]) -> QuakeML:
        return QuakeML.from_bytes(reference_event_assets["quakeml"].read_bytes())

    def test_hypocentre(self, maule: QuakeML) -> None:
        assert maule.time == pd.Timestamp("2010-02-27T06:34:11.530Z")
        assert maule.latitude == -36.122
        assert maule.longitude == -72.898
        assert maule.depth == 22900.0

    def test_public_id_verbatim(self, maule: QuakeML) -> None:
        assert maule.public_id == (
            "quakeml:earthquake.usgs.gov/fdsnws/event/1/query"
            "?eventid=official20100227063411530_30&format=quakeml"
        )

    def test_labels(self, maule: QuakeML) -> None:
        assert maule.magnitude == 8.8
        assert maule.magnitude_type == "mww"
        assert maule.event_type == "earthquake"
        assert maule.description == "2010 Maule, Chile Earthquake"


class TestNarrowing:
    def test_from_bytes_multi_event_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected exactly one event"):
            QuakeML.from_bytes(_doc(_event("smi:e/1"), _event("smi:e/2")))

    def test_all_from_bytes_document_order(self) -> None:
        events = QuakeML.all_from_bytes(_doc(_event("smi:e/1"), _event("smi:e/2")))
        assert [e.public_id for e in events] == ["smi:e/1", "smi:e/2"]

    def test_all_from_bytes_strict_false_skips_unrepresentable_event(self) -> None:
        bad_origin = _ORIGIN.replace("<depth><value>22900</value></depth>", "")
        bad_event = (
            f'<event publicID="smi:e/bad">{bad_origin}'
            "<preferredOriginID>smi:o/1</preferredOriginID></event>"
        )
        doc = _doc(_event("smi:e/good"), bad_event)

        with pytest.raises(ValueError):
            QuakeML.all_from_bytes(doc)  # strict=True default

        with pytest.warns(UserWarning, match="Skipped 1 unrepresentable"):
            events = QuakeML.all_from_bytes(doc, strict=False)
        assert [e.public_id for e in events] == ["smi:e/good"]

    def test_event_id_full_public_id(self) -> None:
        doc = _doc(
            _event("smi:service.iris.edu/fdsnws/event/1/query?eventid=111"),
            _event("smi:service.iris.edu/fdsnws/event/1/query?eventid=222"),
        )
        event = QuakeML.from_bytes(
            doc, event_id="smi:service.iris.edu/fdsnws/event/1/query?eventid=222"
        )
        assert event.public_id.endswith("222")

    def test_event_id_short_eventid_query_form(self) -> None:
        doc = _doc(
            _event(
                "quakeml:earthquake.usgs.gov/fdsnws/event/1/query?eventid=usc000lvb5"
            ),
            _event(
                "quakeml:earthquake.usgs.gov/fdsnws/event/1/query?eventid=usc000abcd"
            ),
        )
        event = QuakeML.from_bytes(doc, event_id="usc000lvb5")
        assert event.public_id.endswith("usc000lvb5")

    def test_event_id_short_path_segment_form(self) -> None:
        doc = _doc(
            _event("smi:service.iris.edu/fdsnws/event/1/3337497"),
            _event("smi:service.iris.edu/fdsnws/event/1/9999999"),
        )
        event = QuakeML.from_bytes(doc, event_id="3337497")
        assert event.public_id.endswith("3337497")

    def test_event_id_short_multi_match_raises(self) -> None:
        doc = _doc(
            _event("smi:a/fdsnws/event/1/query?eventid=42"),
            _event("smi:b/fdsnws/event/1/query?eventid=42"),
        )
        with pytest.raises(ValueError, match="matches 2 events"):
            QuakeML.from_bytes(doc, event_id="42")

    def test_event_id_no_match_raises(self) -> None:
        with pytest.raises(ValueError, match="found 0"):
            QuakeML.from_bytes(_doc(_event("smi:e/1")), event_id="nope")


class TestRejectIgnoreBoundary:
    def test_out_of_slice_elements_ignored(self) -> None:
        noise = (
            '<focalMechanism publicID="smi:fm/1"/>'
            '<pick publicID="smi:p/1"/>'
            '<origin publicID="smi:o/2">'
            "<time><value>2000-01-01T00:00:00Z</value></time>"
            "<latitude><value>0</value></latitude>"
            "<longitude><value>0</value></longitude>"
            "<depth><value>0</value></depth>"
            "<originUncertainty><horizontalUncertainty>0</horizontalUncertainty>"
            "</originUncertainty></origin>"
        )
        rich = QuakeML.from_bytes(_doc(_event("smi:e/1", extra=noise)))
        plain = QuakeML.from_bytes(_doc(_event("smi:e/1")))
        assert (rich.time, rich.latitude, rich.longitude, rich.depth) == (
            plain.time,
            plain.latitude,
            plain.longitude,
            plain.depth,
        )

    def test_slice_field_failure_still_raises(self) -> None:
        broken = _ORIGIN.replace("<depth><value>22900</value></depth>", "")
        doc = _doc(
            f'<event publicID="smi:e/1">{broken}'
            "<preferredOriginID>smi:o/1</preferredOriginID></event>"
        )
        with pytest.raises(ValueError, match="<depth>"):
            QuakeML.from_bytes(doc)


class TestValidation:
    def test_latitude_out_of_range_on_setattr(self) -> None:
        event = QuakeML.from_bytes(_doc(_event("smi:e/1")))
        with pytest.raises(ValueError):
            event.latitude = 200.0

    def test_public_id_is_parse_time_provenance(self) -> None:
        event = QuakeML.from_bytes(_doc(_event("smi:e/1")))
        event.latitude = -10.0
        assert event.public_id == "smi:e/1"
