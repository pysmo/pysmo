"""Tests for pysmo.lib.io._quakeml."""

from pathlib import Path

import pandas as pd
import pytest

from pysmo.lib.io._quakeml import parse_quakeml

_HEADER = (
    '<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2" '
    'xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">'
)


def _doc(events: str, *, header: str = _HEADER) -> bytes:
    return (
        f'<?xml version="1.0"?>\n{header}\n'
        f'  <eventParameters publicID="smi:example/catalogue">\n'
        f"{events}\n"
        f"  </eventParameters>\n</q:quakeml>"
    ).encode()


def _event(
    *,
    public_id: str = "smi:example/event/1",
    origins: str | None = None,
    magnitudes: str = "",
    preferred_origin: str | None = "smi:example/origin/1",
    preferred_magnitude: str | None = None,
    extra: str = "",
) -> str:
    if origins is None:
        origins = _origin()
    pref_o = (
        f"<preferredOriginID>{preferred_origin}</preferredOriginID>"
        if preferred_origin is not None
        else ""
    )
    pref_m = (
        f"<preferredMagnitudeID>{preferred_magnitude}</preferredMagnitudeID>"
        if preferred_magnitude is not None
        else ""
    )
    return (
        f'    <event publicID="{public_id}">\n'
        f"      {origins}\n      {magnitudes}\n      {pref_o}{pref_m}{extra}\n"
        f"    </event>"
    )


def _origin(
    *,
    public_id: str = "smi:example/origin/1",
    time: str | None = "2010-02-27T06:34:11.53Z",
    latitude: str | None = "-36.122",
    longitude: str | None = "-72.898",
    depth: str | None = "22900",
) -> str:
    parts = [f'<origin publicID="{public_id}">']
    if time is not None:
        parts.append(f"<time><value>{time}</value></time>")
    if latitude is not None:
        parts.append(f"<latitude><value>{latitude}</value></latitude>")
    if longitude is not None:
        parts.append(f"<longitude><value>{longitude}</value></longitude>")
    if depth is not None:
        parts.append(f"<depth><value>{depth}</value></depth>")
    parts.append("</origin>")
    return "".join(parts)


def _magnitude(
    *,
    public_id: str = "smi:example/magnitude/1",
    mag: str = "8.8",
    mag_type: str = "Mw",
) -> str:
    return (
        f'<magnitude publicID="{public_id}">'
        f"<mag><value>{mag}</value></mag><type>{mag_type}</type></magnitude>"
    )


class TestParseQuakeml:
    def test_single_event_single_origin_no_pointer(self) -> None:
        events = parse_quakeml(_doc(_event(preferred_origin=None)))
        assert len(events) == 1
        assert events[0].latitude == -36.122
        assert events[0].longitude == -72.898
        assert events[0].depth == 22900.0
        assert events[0].time == pd.Timestamp("2010-02-27T06:34:11.53Z")
        assert events[0].magnitude is None

    def test_multi_event_catalogue(self) -> None:
        events = parse_quakeml(
            _doc(
                _event(public_id="smi:e/1")
                + "\n"
                + _event(public_id="smi:e/2", preferred_origin=None)
            )
        )
        assert [e.public_id for e in events] == ["smi:e/1", "smi:e/2"]

    def test_preferred_origin_selects_one_of_several(self) -> None:
        origins = _origin(public_id="smi:o/A", depth="1000") + _origin(
            public_id="smi:o/B", depth="22900"
        )
        events = parse_quakeml(
            _doc(_event(origins=origins, preferred_origin="smi:o/B"))
        )
        assert events[0].depth == 22900.0

    @pytest.mark.parametrize("missing", ["time", "latitude", "longitude", "depth"])
    def test_missing_required_origin_element_raises_naming_public_id(
        self, missing: str
    ) -> None:
        origin = _origin(**{missing: None})  # type: ignore[arg-type]
        with pytest.raises(ValueError, match=r"smi:example/event/1.*<" + missing + ">"):
            parse_quakeml(_doc(_event(origins=origin)))

    def test_second_event_incomplete_fails_whole_parse(self) -> None:
        doc = _doc(
            _event(public_id="smi:e/good")
            + "\n"
            + _event(public_id="smi:e/bad", origins=_origin(depth=None))
        )
        with pytest.raises(ValueError, match=r"smi:e/bad"):
            parse_quakeml(doc)

    def test_multiple_bad_events_names_first_and_count(self) -> None:
        doc = _doc(
            _event(public_id="smi:e/bad1", origins=_origin(depth=None))
            + "\n"
            + _event(public_id="smi:e/bad2", origins=_origin(time=None))
        )
        with pytest.raises(ValueError, match=r"smi:e/bad1.*2 events"):
            parse_quakeml(doc)

    def test_no_pointer_and_multiple_origins_raises(self) -> None:
        origins = _origin(public_id="smi:o/A") + _origin(public_id="smi:o/B")
        with pytest.raises(ValueError, match="ambiguous preferred origin"):
            parse_quakeml(_doc(_event(origins=origins, preferred_origin=None)))

    def test_no_magnitude_pointer_and_multiple_magnitudes_raises(self) -> None:
        magnitudes = _magnitude(public_id="smi:m/A") + _magnitude(public_id="smi:m/B")
        with pytest.raises(ValueError, match="ambiguous preferred magnitude"):
            parse_quakeml(_doc(_event(magnitudes=magnitudes)))

    def test_multiple_magnitudes_with_valid_pointer_resolves(self) -> None:
        magnitudes = _magnitude(public_id="smi:m/A", mag="7.0") + _magnitude(
            public_id="smi:m/B", mag="8.8"
        )
        events = parse_quakeml(
            _doc(_event(magnitudes=magnitudes, preferred_magnitude="smi:m/B"))
        )
        assert events[0].magnitude == 8.8

    def test_zero_magnitudes_is_none_not_error(self) -> None:
        events = parse_quakeml(_doc(_event(magnitudes="")))
        assert events[0].magnitude is None
        assert events[0].magnitude_type is None

    def test_time_without_zone_parsed_as_utc(self) -> None:
        origin = _origin(time="2010-02-27T06:34:11.53")
        events = parse_quakeml(_doc(_event(origins=origin)))
        assert events[0].time == pd.Timestamp("2010-02-27T06:34:11.53Z")
        assert events[0].time.tz is not None

    def test_negative_depth_preserved(self) -> None:
        events = parse_quakeml(_doc(_event(origins=_origin(depth="-500"))))
        assert events[0].depth == -500.0

    def test_single_default_namespace_document(self) -> None:
        header = '<quakeml xmlns="http://quakeml.org/xmlns/bed/1.2">'
        doc = (
            f'<?xml version="1.0"?>\n{header}\n'
            '  <eventParameters publicID="smi:c">\n'
            f"{_event(preferred_origin=None)}\n"
            "  </eventParameters>\n</quakeml>"
        ).encode()
        events = parse_quakeml(doc)
        assert events[0].latitude == -36.122

    def test_not_well_formed_xml_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="well-formed"):
            parse_quakeml(b"<q:quakeml><eventParameters>truncated")

    def test_non_quakeml_root_rejected(self) -> None:
        with pytest.raises(ValueError, match="Not a QuakeML document"):
            parse_quakeml(b'<?xml version="1.0"?><rss><channel/></rss>')

    def test_no_event_parameters_rejected(self) -> None:
        doc = f'<?xml version="1.0"?>\n{_HEADER}\n</q:quakeml>'.encode()
        with pytest.raises(ValueError, match="no <eventParameters>"):
            parse_quakeml(doc)

    def test_missing_public_id_rejected(self) -> None:
        doc = _doc("    <event>" + _origin() + "</event>")
        with pytest.raises(ValueError, match="no publicID"):
            parse_quakeml(doc)

    def test_metadata_present(self) -> None:
        extra = (
            "<type>explosion</type><description><text>Somewhere</text></description>"
        )
        events = parse_quakeml(
            _doc(_event(magnitudes=_magnitude(mag_type="mb"), extra=extra))
        )
        assert events[0].event_type == "explosion"
        assert events[0].description == "Somewhere"
        assert events[0].magnitude_type == "mb"

    def test_metadata_absent(self) -> None:
        events = parse_quakeml(_doc(_event()))
        assert events[0].event_type is None
        assert events[0].description is None


class TestReferenceFixture:
    def test_maule_2010(self, reference_event_assets: dict[str, Path]) -> None:
        events = parse_quakeml(reference_event_assets["quakeml"].read_bytes())
        assert len(events) == 1
        event = events[0]
        assert event.time == pd.Timestamp("2010-02-27T06:34:11.530Z")
        assert event.latitude == -36.122
        assert event.longitude == -72.898
        assert event.depth == 22900.0
        assert event.magnitude == 8.8
        assert event.magnitude_type == "mww"
        assert event.event_type == "earthquake"
        assert event.description == "2010 Maule, Chile Earthquake"
