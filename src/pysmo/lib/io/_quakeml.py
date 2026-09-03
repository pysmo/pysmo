"""Low-level parsing of the FDSN QuakeML 1.2 format (event hypocentre + time only).

This module implements the parsing side of a narrow slice of
[QuakeML 1.2](https://quakeml.org/): per event, the `publicID` and the
preferred origin's time, latitude, longitude and depth, plus the preferred
magnitude, event type and description where present. It returns
uninterpreted `_RawEvent` instances (one per `<event>`) without
constructing any `pysmo` type. Interpretation into an
[`Event`][pysmo.Event]-compatible object happens one layer up, in
[`pysmo.classes.QuakeML`][].

Focal mechanisms, moment tensors, origin uncertainties, picks, arrivals,
amplitudes, station magnitudes, competing origin/magnitude solutions and
creation metadata are all deliberately out of scope.
"""

import warnings
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import TypeIs

import pandas as pd

from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = ["parse_quakeml"]

_QUAKEML_NS = frozenset(
    {
        "http://quakeml.org/xmlns/quakeml/1.2",
        "http://quakeml.org/xmlns/bed/1.2",
    }
)
"""The two namespace URIs QuakeML 1.2 splits its umbrella and body elements
across. Body elements are resolved by local name within either; some
producers emit the whole document in one default namespace rather than
splitting root from body."""

_REQUIRED_ORIGIN_ELEMENTS = ("time", "latitude", "longitude", "depth")
"""Preferred-origin sub-elements the [`Event`][pysmo.Event] protocol needs.
`<depth>` is schema-optional (`0..1`) but non-optional here (see
[`pysmo.classes.QuakeML`][])."""


@dataclass
class _RawEvent:
    """A single uninterpreted `<event>`'s narrow slice."""

    public_id: str
    time: pd.Timestamp
    latitude: float
    longitude: float
    depth: float
    magnitude: float | None
    magnitude_type: str | None
    event_type: str | None
    description: str | None


def _local_name(tag: str) -> str:
    """Return the local part of a (possibly namespaced) element tag."""
    return tag.rpartition("}")[2] if tag.startswith("{") else tag


def _namespace_uri(tag: str) -> str | None:
    """Return the namespace URI of a namespaced element tag, or `None`."""
    return tag[1:].partition("}")[0] if tag.startswith("{") else None


def _iter_children(elem: ET.Element, local: str) -> Iterator[ET.Element]:
    """Yield `elem`'s children with the given local name (QuakeML namespace)."""
    for child in elem:
        uri = _namespace_uri(child.tag)
        if _local_name(child.tag) == local and (uri is None or uri in _QUAKEML_NS):
            yield child


def _find_child(elem: ET.Element, local: str) -> ET.Element | None:
    """Return `elem`'s first direct child with the given local name, or `None`."""
    return next(_iter_children(elem, local), None)


def _child_text(elem: ET.Element, local: str) -> str | None:
    """Stripped text of `elem`'s first `<local>` child, or `None` if absent or empty."""
    child = _find_child(elem, local)
    if child is None or child.text is None or not child.text.strip():
        return None
    return child.text.strip()


def _quantity_value(parent: ET.Element, local: str) -> str | None:
    """Text of `parent/<local>/<value>` (a QuakeML quantity element), or `None`."""
    quantity = _find_child(parent, local)
    if quantity is None:
        return None
    return _child_text(quantity, "value")


def _all_required_present(
    values: Mapping[str, str | None],
) -> TypeIs[Mapping[str, str]]:
    """True when every required origin element has a value (narrows to `str`)."""
    return all(value is not None for value in values.values())


def _resolve_preferred(
    candidates: list[ET.Element], preferred_id: str | None
) -> ET.Element | None:
    """Resolve the preferred `<origin>` or `<magnitude>` element.

    Returns the pointed-to element if the pointer resolves; otherwise the
    sole inlined candidate if there is exactly one; otherwise `None` for
    zero candidates. Raises `ValueError` for more than one candidate with no
    resolving pointer, an ambiguity that cannot be resolved without
    guessing.
    """
    if preferred_id is not None:
        for candidate in candidates:
            if candidate.get("publicID") == preferred_id:
                return candidate
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return None
    raise ValueError(
        f"{len(candidates)} candidates and no resolvable preferred pointer"
    )


def _parse_magnitude(
    magnitude_elem: ET.Element | None, public_id: str
) -> tuple[float | None, str | None]:
    """Parse a preferred `<magnitude>` element into a numeric value and type.

    Returns `(None, None)` when `magnitude_elem` is `None`. Raises
    `ValueError` when the `<mag>` text is present but unparseable.
    """
    if magnitude_elem is None:
        return None, None
    mag_text = _quantity_value(magnitude_elem, "mag")
    magnitude: float | None = None
    if mag_text is not None:
        try:
            magnitude = float(mag_text)
        except ValueError as exc:
            raise ValueError(
                f"event {public_id!r}: could not parse magnitude value ({exc})"
            )
    return magnitude, _child_text(magnitude_elem, "type")


def _first_description(event: ET.Element) -> str | None:
    """Text of the first `<description>` child that has non-empty text, or `None`."""
    for description_elem in _iter_children(event, "description"):
        text = _child_text(description_elem, "text")
        if text is not None:
            return text
    return None


def _parse_event(event: ET.Element, position: int) -> _RawEvent:
    """Parse one `<event>` element into a `_RawEvent`.

    Raises `ValueError` for any part that cannot be represented.
    """
    public_id = event.get("publicID")
    if not public_id:
        raise ValueError(f"event at position {position} has no publicID attribute")

    origins = list(_iter_children(event, "origin"))
    magnitudes = list(_iter_children(event, "magnitude"))

    try:
        origin = _resolve_preferred(origins, _child_text(event, "preferredOriginID"))
    except ValueError as exc:
        raise ValueError(f"event {public_id!r}: ambiguous preferred origin ({exc})")
    if origin is None:
        raise ValueError(f"event {public_id!r}: no origin found")

    values = {name: _quantity_value(origin, name) for name in _REQUIRED_ORIGIN_ELEMENTS}
    if not _all_required_present(values):
        missing = [f"<{name}>" for name, text in values.items() if text is None]
        raise ValueError(
            f"event {public_id!r}: preferred origin is missing required "
            + f"element(s): {', '.join(missing)}"
        )

    try:
        time = convert_to_utc_timestamp(values["time"])
        latitude = float(values["latitude"])
        longitude = float(values["longitude"])
        depth = float(values["depth"])
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"event {public_id!r}: could not parse a preferred origin value ({exc})"
        )

    try:
        magnitude_elem = _resolve_preferred(
            magnitudes, _child_text(event, "preferredMagnitudeID")
        )
    except ValueError as exc:
        raise ValueError(f"event {public_id!r}: ambiguous preferred magnitude ({exc})")
    magnitude, magnitude_type = _parse_magnitude(magnitude_elem, public_id)

    description = _first_description(event)

    return _RawEvent(
        public_id=public_id,
        time=time,
        latitude=latitude,
        longitude=longitude,
        depth=depth,
        magnitude=magnitude,
        magnitude_type=magnitude_type,
        event_type=_child_text(event, "type"),
        description=description,
    )


def parse_quakeml(xml: bytes, *, strict: bool = True) -> list[_RawEvent]:
    """Parse the event hypocentre and origin time from a QuakeML 1.2 document.

    Returns one entry per `<event>` found. Only the preferred origin's
    time/latitude/longitude/depth, and (where present) the preferred
    magnitude, event type and first description, are read.

    Args:
        xml: Raw QuakeML 1.2 document bytes (as returned by any
            `fdsnws-event` service).
        strict: If `True` (default), a single unrepresentable event fails
            the whole document. If `False`, unrepresentable events are
            skipped and a `UserWarning` reports how many; useful for a
            broad catalogue query where a few malformed origins should not
            discard the rest.

    Returns:
        One uninterpreted event per representable `<event>` found, in
        document order.

    Raises:
        ValueError: If `xml` is not well-formed XML, its root is not a
            QuakeML `<quakeml>` element, or it has no `<eventParameters>`.
            When `strict` is `True`, also if any event has no `publicID`, no
            resolvable preferred origin, a preferred origin missing
            `<time>`/`<latitude>`/`<longitude>`/`<depth>`, an ambiguous
            preferred origin/magnitude, or an unparseable numeric or
            timestamp value; the message names the first such event and the
            count.

    Examples:
        ```python
        >>> from pysmo.lib.io._quakeml import parse_quakeml
        >>> xml = b'''<?xml version="1.0"?>
        ... <q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
        ...            xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
        ...   <eventParameters publicID="smi:example/catalogue">
        ...     <event publicID="smi:example/event/1">
        ...       <description><text>Example</text></description>
        ...       <origin publicID="smi:example/origin/1">
        ...         <time><value>2010-02-27T06:34:11.53Z</value></time>
        ...         <latitude><value>-36.122</value></latitude>
        ...         <longitude><value>-72.898</value></longitude>
        ...         <depth><value>22900</value></depth>
        ...       </origin>
        ...       <magnitude publicID="smi:example/magnitude/1">
        ...         <mag><value>8.8</value></mag>
        ...         <type>Mw</type>
        ...       </magnitude>
        ...       <type>earthquake</type>
        ...     </event>
        ...   </eventParameters>
        ... </q:quakeml>'''
        >>> events = parse_quakeml(xml)
        >>> len(events)
        1
        >>> events[0].latitude, events[0].depth, events[0].magnitude
        (-36.122, 22900.0, 8.8)
        >>>
        ```
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f"Not well-formed XML: {exc}") from exc
    root_uri = _namespace_uri(root.tag)
    if _local_name(root.tag) != "quakeml" or (
        root_uri is not None and root_uri not in _QUAKEML_NS
    ):
        raise ValueError(
            f"Not a QuakeML document: root element is <{_local_name(root.tag)}>."
        )

    event_parameters = _find_child(root, "eventParameters")
    if event_parameters is None:
        raise ValueError("QuakeML document has no <eventParameters> element.")

    results: list[_RawEvent] = []
    errors: list[str] = []
    for position, event in enumerate(_iter_children(event_parameters, "event")):
        try:
            results.append(_parse_event(event, position))
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        message = errors[0]
        if len(errors) > 1:
            message += f" ({len(errors)} events in the document could not be parsed)"
        if strict:
            raise ValueError(message)
        warnings.warn(
            f"Skipped {len(errors)} unrepresentable event(s); first: {message}",
            UserWarning,
            stacklevel=2,
        )

    return results
