"""FDSN QuakeML event metadata import class compatible with pysmo types."""

import re
from typing import Self

import pandas as pd
from attrs import converters, define, field, setters, validators

from pysmo.lib.io._quakeml import _RawEvent, parse_quakeml
from pysmo.lib.validators import convert_to_utc_timestamp
from pysmo.tools.web import QuakeMLOrderBy, fetch_quakeml
from pysmo.typing import UtcTimestamp

__all__ = ["QuakeML"]

_EVENTID_QUERY = re.compile(r"[?&]eventid=([^&]+)")


def _short_id(public_id: str) -> str:
    """Return a source-assigned short id for `public_id`.

    The value of a trailing `eventid=` query parameter if present, otherwise
    the final path segment of the URI (query string stripped).
    """
    match = _EVENTID_QUERY.search(public_id)
    if match:
        return match.group(1)
    return public_id.split("?", 1)[0].rstrip("/").rpartition("/")[2]


@define(kw_only=True)
class QuakeML:
    """Import class for FDSN QuakeML event metadata.

    Reads the hypocentre and origin time of a seismic event from a
    QuakeML 1.2 document (as returned by any `fdsnws-event` service) and
    exposes it as an [`Event`][pysmo.Event]-compatible object. A QuakeML
    document commonly describes many events;
    [`from_bytes`][pysmo.classes.QuakeML.from_bytes] narrows to one,
    [`all_from_bytes`][pysmo.classes.QuakeML.all_from_bytes] returns every
    event found.

    Only the preferred origin's hypocentre and time are read. Focal
    mechanisms, picks, arrivals, origin uncertainties and competing
    origin/magnitude solutions in the document are not represented.

    An object satisfying the full [`Station`][pysmo.Station] or
    [`Event`][pysmo.Event] protocol for another data source is built
    separately (e.g. a [`MiniEvent`][pysmo.MiniEvent], or via
    [`clone_to_mini`][pysmo.functions.clone_to_mini]); `QuakeML` does not
    fabricate one.

    Examples:
        ```python
        >>> from pysmo.classes import QuakeML
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
        >>> event = QuakeML.from_bytes(xml)
        >>> event.latitude, event.longitude, event.depth
        (-36.122, -72.898, 22900.0)
        >>> event.magnitude, event.magnitude_type
        (8.8, 'Mw')
        >>> event.public_id
        'smi:example/event/1'
        >>>
        ```
    """

    time: UtcTimestamp = field(
        converter=convert_to_utc_timestamp,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event origin time."""

    latitude: float = field(
        converter=float,
        validator=[validators.ge(-90), validators.le(90)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=float,
        validator=[validators.gt(-180), validators.le(180)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event longitude from -180 to 180 degrees."""

    depth: float = field(
        converter=float, on_setattr=setters.pipe(setters.convert, setters.validate)
    )
    """Hypocentre depth in metres, positive downwards, as recorded in the
    source catalogue — relative to sea level; may be negative for events
    above sea level. (The datum detail lives here, not on
    [`Event.depth`][pysmo.Event.depth], because it is format-specific.)"""

    public_id: str = field(
        validator=validators.instance_of(str), on_setattr=setters.validate
    )
    """QuakeML `publicID` of the event this instance was parsed from,
    preserved verbatim. It is a dependable unique key for records from one
    catalogue, but not a canonical per-earthquake key across a catalogue
    merged from several sources (each agency assigns its own). Parse-time
    provenance: not updated when other attributes change."""

    magnitude: float | None = field(default=None, converter=converters.optional(float))
    """Preferred magnitude value, or `None` if the document has none."""

    magnitude_type: str | None = field(default=None)
    """Preferred magnitude type (e.g. `"Mw"`), or `None`."""

    event_type: str | None = field(default=None)
    """QuakeML `event/type` (e.g. `"earthquake"`, `"explosion"`), or `None`."""

    description: str | None = field(default=None)
    """First `event/description/text` (e.g. a Flinn-Engdahl region or event
    name), or `None`."""

    @classmethod
    def from_bytes(cls, xml: bytes, *, event_id: str | None = None) -> Self:
        """Create a new instance from a QuakeML document, narrowing to one event.

        Args:
            xml: Raw QuakeML 1.2 document bytes.
            event_id: Event to select when `xml` describes more than one.
                Matched against each event's full `publicID`, or — as a
                short form — against the trailing `eventid=` query-parameter
                value or the final path segment of the `publicID`. If
                `None`, `xml` must describe exactly one event.

        Returns:
            A new QuakeML instance for the selected event.

        Raises:
            ValueError: If `xml` is malformed or describes an event that
                cannot be represented (see
                [`pysmo.classes.QuakeML`][]), if `event_id` is `None` and
                `xml` does not describe exactly one event, or if `event_id`
                matches zero or (in its short form) more than one event.

        Tip: See Also
            [`QuakeML.all_from_bytes`][pysmo.classes.QuakeML.all_from_bytes]:
            Return every event in the document without narrowing to one.
        """
        events = cls.all_from_bytes(xml)
        if event_id is None:
            if len(events) != 1:
                raise ValueError(
                    "Expected exactly one event in the given QuakeML, found "
                    + f"{len(events)}: {[event.public_id for event in events]}."
                )
            return events[0]

        exact = [event for event in events if event.public_id == event_id]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise ValueError(
                f"event_id {event_id!r} matches {len(exact)} events by publicID."
            )

        short = [event for event in events if _short_id(event.public_id) == event_id]
        if len(short) == 1:
            return short[0]
        if len(short) > 1:
            raise ValueError(
                f"event_id {event_id!r} matches {len(short)} events: "
                + f"{[event.public_id for event in short]}."
            )
        raise ValueError(
            f"Expected exactly one event matching event_id {event_id!r}, found 0."
        )

    @classmethod
    def all_from_bytes(cls, xml: bytes) -> list[Self]:
        """Create one instance per `<event>` in a QuakeML document.

        Args:
            xml: Raw QuakeML 1.2 document bytes.

        Returns:
            One QuakeML instance per event found, in document order.

        Raises:
            ValueError: If `xml` is malformed or contains any event that
                cannot be represented — a single unrepresentable event
                fails the whole parse (see [`pysmo.classes.QuakeML`][]).
        """
        return [cls._from_raw(raw) for raw in parse_quakeml(xml)]

    @classmethod
    def fetch(cls, *, event_id: str) -> Self:
        """Fetch and parse a single event from the USGS fdsnws-event service.

        Fetches exactly one event by the service's event id. To fetch a
        catalogue, use
        [`all_from_query`][pysmo.classes.QuakeML.all_from_query]; to fetch
        once and parse later (e.g. offline), use
        [`pysmo.tools.web.fetch_quakeml`][] with
        [`from_bytes`][pysmo.classes.QuakeML.from_bytes].

        Args:
            event_id: The service's event id.

        Returns:
            A new QuakeML instance for the fetched event.

        Raises:
            ValueError: If the response cannot be parsed or does not
                describe exactly one event.
            urllib3.exceptions.ResponseError: If the event web service
                returns an HTTP error.
        """
        return cls.from_bytes(fetch_quakeml(eventid=event_id))

    @classmethod
    def all_from_query(
        cls,
        *,
        starttime: pd.Timestamp | None = None,
        endtime: pd.Timestamp | None = None,
        updatedafter: pd.Timestamp | None = None,
        minlatitude: float | None = None,
        maxlatitude: float | None = None,
        minlongitude: float | None = None,
        maxlongitude: float | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        minradius: float | None = None,
        maxradius: float | None = None,
        mindepth_km: float | None = None,
        maxdepth_km: float | None = None,
        minmagnitude: float | None = None,
        maxmagnitude: float | None = None,
        magnitudetype: str | None = None,
        eventtype: str | None = None,
        eventid: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        orderby: QuakeMLOrderBy | None = None,
        catalog: str | None = None,
        contributor: str | None = None,
    ) -> list[Self]:
        """Fetch and parse a catalogue of events from the USGS fdsnws-event service.

        A one-step convenience over
        [`pysmo.tools.web.fetch_quakeml`][] followed by
        [`all_from_bytes`][pysmo.classes.QuakeML.all_from_bytes]. The
        parameters and their meanings are exactly those of `fetch_quakeml`;
        `mindepth_km` / `maxdepth_km` are in **kilometres** while the parsed
        [`depth`][pysmo.classes.QuakeML] is in metres.

        Returns:
            One QuakeML instance per event found, in the service's order.

        Raises:
            ValueError: If the response cannot be parsed, or any event in it
                cannot be represented.
            urllib3.exceptions.ResponseError: If the event web service
                returns an HTTP error, including a 404 when nothing matches.
        """
        return cls.all_from_bytes(
            fetch_quakeml(
                starttime=starttime,
                endtime=endtime,
                updatedafter=updatedafter,
                minlatitude=minlatitude,
                maxlatitude=maxlatitude,
                minlongitude=minlongitude,
                maxlongitude=maxlongitude,
                latitude=latitude,
                longitude=longitude,
                minradius=minradius,
                maxradius=maxradius,
                mindepth_km=mindepth_km,
                maxdepth_km=maxdepth_km,
                minmagnitude=minmagnitude,
                maxmagnitude=maxmagnitude,
                magnitudetype=magnitudetype,
                eventtype=eventtype,
                eventid=eventid,
                limit=limit,
                offset=offset,
                orderby=orderby,
                catalog=catalog,
                contributor=contributor,
            )
        )

    @classmethod
    def _from_raw(cls, raw: _RawEvent) -> Self:
        return cls(
            time=raw.time,
            latitude=raw.latitude,
            longitude=raw.longitude,
            depth=raw.depth,
            public_id=raw.public_id,
            magnitude=raw.magnitude,
            magnitude_type=raw.magnitude_type,
            event_type=raw.event_type,
            description=raw.description,
        )
