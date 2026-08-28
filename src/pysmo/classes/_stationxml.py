"""FDSN StationXML import class compatible with pysmo types."""

from collections import defaultdict
from collections.abc import Iterable
from typing import Self

import pandas as pd
from attrs import converters, define, field, validators

from pysmo import MiniResponseStage, MiniStagedResponse, Station
from pysmo.lib.io._stationxml import _RawStationEpoch, parse_stationxml
from pysmo.lib.validators import convert_to_utc_timestamp
from pysmo.tools.web import fetch_stationxml

__all__ = ["StationXML", "resolve_epochs"]


def _matching_epochs(
    epochs: list[_RawStationEpoch],
    time: pd.Timestamp | None,
    *,
    network: str | None = None,
    station: str | None = None,
    location: str | None = None,
    channel: str | None = None,
) -> list[_RawStationEpoch]:
    if network is not None:
        epochs = [epoch for epoch in epochs if epoch.network == network]
    if station is not None:
        epochs = [epoch for epoch in epochs if epoch.station == station]
    if location is not None:
        epochs = [epoch for epoch in epochs if epoch.location == location]
    if channel is not None:
        epochs = [epoch for epoch in epochs if epoch.channel == channel]
    if time is not None:
        time = convert_to_utc_timestamp(time)
        return [
            epoch
            for epoch in epochs
            if epoch.start_date <= time
            and (epoch.end_date is None or time < epoch.end_date)
        ]
    return [epoch for epoch in epochs if epoch.end_date is None]


@define(kw_only=True)
class StationXML:
    r"""Import class for FDSN StationXML station metadata.

    Reads one `<Channel>` epoch from a
    [FDSN StationXML](http://www.fdsn.org/xml/station/) document and exposes
    it as a [`Station`][pysmo.Station]-compatible object: NSLC identity,
    coordinates, the epoch's validity window, and — when the document was
    fetched at `level=response` — the instrument
    [`response`][pysmo.classes.StationXML.response].

    A document commonly covers a channel's full history, i.e. several
    epochs. [`from_bytes`][pysmo.classes.StationXML.from_bytes] narrows to
    one (matching a time, or the currently-open one);
    [`all_from_bytes`][pysmo.classes.StationXML.all_from_bytes] returns every
    epoch found. Accessing
    [`response`][pysmo.classes.StationXML.response] raises for an epoch
    parsed from a `level=channel` / `level=station` document (e.g. a bulk
    inventory fetched with
    [`pysmo.tools.web.fetch_station_inventory`][]) — guard it with
    [`has_response`][pysmo.classes.StationXML.has_response].
    [`fetch`][pysmo.classes.StationXML.fetch] always populates it.

    Examples:
        ```python
        >>> from pysmo import Location, Response, Station
        >>> from pysmo.classes import StationXML
        >>> xml = b'''\
        ... <?xml version="1.0"?>
        ... <FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
        ...   <Network code="IU">
        ...     <Station code="ANMO">
        ...       <Latitude>34.9</Latitude><Longitude>-106.5</Longitude>
        ...       <Channel code="BHZ" locationCode="00"
        ...                startDate="2018-07-09T20:45:00.0000">
        ...         <Latitude>34.945981</Latitude><Longitude>-106.457133</Longitude>
        ...         <Elevation>1632.7</Elevation>
        ...         <Response>
        ...           <InstrumentSensitivity>
        ...             <Value>1.98475E9</Value>
        ...             <InputUnits><Name>m/s</Name></InputUnits>
        ...           </InstrumentSensitivity>
        ...           <Stage number="1">
        ...             <PolesZeros>
        ...               <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
        ...               <NormalizationFactor>5.03773E14</NormalizationFactor>
        ...               <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
        ...               <Pole number="0"><Real>-0.037</Real><Imaginary>0.037</Imaginary></Pole>
        ...             </PolesZeros>
        ...             <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
        ...           </Stage>
        ...         </Response>
        ...       </Channel>
        ...     </Station>
        ...   </Network>
        ... </FDSNStationXML>'''
        >>> station = StationXML.from_bytes(xml)
        >>> isinstance(station, Station)
        True
        >>> isinstance(station, Location)
        True
        >>> station.network, station.name, station.channel
        ('IU', 'ANMO', 'BHZ')
        >>> isinstance(station.response, Response)
        True
        >>>
        ```
    """

    network: str = field(validator=validators.instance_of(str))
    """Network code."""

    name: str = field(validator=validators.instance_of(str))
    """Station code."""

    location: str = field(validator=validators.instance_of(str))
    """Location code (empty for a `level=station` epoch)."""

    channel: str = field(validator=validators.instance_of(str))
    """Channel code (empty for a `level=station` epoch)."""

    latitude: float = field(converter=float)
    """Latitude in degrees."""

    longitude: float = field(converter=float)
    """Longitude in degrees."""

    elevation: float | None = field(default=None, converter=converters.optional(float))
    """Elevation in metres, or `None` if the document omits it."""

    start_date: pd.Timestamp = field(converter=convert_to_utc_timestamp)
    """Start of this metadata epoch."""

    end_date: pd.Timestamp | None = field(
        default=None, converter=converters.optional(convert_to_utc_timestamp)
    )
    """End of this metadata epoch, or `None` if still open."""

    _response: MiniStagedResponse | None = field(
        default=None,
        alias="response",
        repr=lambda value: "None" if value is None else "<MiniStagedResponse>",
    )
    """Backing store for [`response`][pysmo.classes.StationXML.response];
    `None` when the source document carried no `<Response>`."""

    @property
    def has_response(self) -> bool:
        """Whether this epoch carries an instrument response.

        Guard [`response`][pysmo.classes.StationXML.response] with this when
        an epoch might have come from a `level=channel` / `level=station`
        document (e.g. a bulk inventory).
        """
        return self._response is not None

    @property
    def response(self) -> MiniStagedResponse:
        """This epoch's instrument response.

        Satisfies [`Response`][pysmo.Response] and
        [`StagedResponse`][pysmo.StagedResponse] (`stages` is empty for a
        document with no digital decimation stages).

        Raises:
            ValueError: If this epoch was parsed from a document with no
                `<Response>` — check
                [`has_response`][pysmo.classes.StationXML.has_response]
                first, or fetch at `level=response`
                ([`StationXML.fetch`][pysmo.classes.StationXML.fetch]).
        """
        if self._response is None:
            raise ValueError(
                f"{self.network}.{self.name}.{self.location}.{self.channel} was "
                "parsed from a document with no <Response>; fetch it at "
                "level=response."
            )
        return self._response

    @classmethod
    def from_bytes(
        cls,
        xml: bytes,
        *,
        time: pd.Timestamp | None = None,
        network: str | None = None,
        station: str | None = None,
        location: str | None = None,
        channel: str | None = None,
    ) -> Self:
        """Create a new instance from a StationXML document, selecting one epoch.

        A document is not guaranteed to cover a single channel — a bulk or
        wildcard query can cover several networks and stations, each with
        every location/channel combination and its own epoch history.
        `network`/`station`/`location`/`channel` narrow to one before *time*
        is applied; without them, a document covering more than one raises
        the same "more than one epoch" error as an ambiguous *time*.

        Args:
            xml: Raw StationXML document bytes.
            time: Timestamp used to select the epoch. If `None`, the
                currently-open epoch (no end date) is selected.
            network: Network code to narrow to, if `xml` covers more than one.
            station: Station code to narrow to, if `xml` covers more than one.
            location: Location code to narrow to, if `xml` covers more than one.
            channel: Channel code to narrow to, if `xml` covers more than one.

        Returns:
            A new StationXML instance for the epoch active at *time* (or
            currently open, if *time* is `None`).

        Raises:
            ValueError: If, after narrowing, zero or more than one epoch
                matches *time* (or "currently open", if *time* is `None`).

        Tip: See Also
            [`StationXML.all_from_bytes`][pysmo.classes.StationXML.all_from_bytes]:
            Parse every epoch in the document without narrowing to one.
        """
        matches = _matching_epochs(
            parse_stationxml(xml),
            time,
            network=network,
            station=station,
            location=location,
            channel=channel,
        )
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one epoch in the given StationXML at "
                f"{'the currently open epoch' if time is None else time}"
                f"{f', network {network!r}' if network is not None else ''}"
                f"{f', station {station!r}' if station is not None else ''}"
                f"{f', location {location!r}' if location is not None else ''}"
                f"{f', channel {channel!r}' if channel is not None else ''}, "
                f"found {len(matches)}."
            )
        return cls._from_raw(matches[0])

    @classmethod
    def all_from_bytes(cls, xml: bytes) -> list[Self]:
        """Create one instance per `<Channel>` epoch in a StationXML document.

        Unlike [`from_bytes`][pysmo.classes.StationXML.from_bytes], this does
        not narrow — a document covering a channel's full history returns
        several, each with its own NSLC / `start_date` / `end_date`.

        Args:
            xml: Raw StationXML document bytes.

        Returns:
            One StationXML instance per epoch found, in document order.
        """
        return [cls._from_raw(raw) for raw in parse_stationxml(xml)]

    @classmethod
    def fetch(cls, *, station: Station, time: pd.Timestamp | None = None) -> Self:
        """Fetch one channel's response epoch from the EarthScope FDSN station web service.

        Fetches the full response history for the channel in one
        `level=response` request and narrows client-side to the epoch active
        at *time* (or the currently-open one). To fetch once and interpret
        later, use [`pysmo.tools.web.fetch_stationxml`][] with
        [`from_bytes`][pysmo.classes.StationXML.from_bytes] /
        [`all_from_bytes`][pysmo.classes.StationXML.all_from_bytes].

        Args:
            station: Any object satisfying the [`Station`][pysmo.Station]
                protocol. Provides the network, station, location and
                channel for the request.
            time: Timestamp used to select the epoch. If `None`, the
                currently-open epoch is selected.

        Returns:
            A new StationXML instance with `response` populated.

        Raises:
            ValueError: If zero or more than one epoch matches *time*, or if
                the fetched document carries no `<Response>`.
            urllib3.exceptions.ResponseError: If the station web service
                returns an HTTP error.

        Examples:
            <!-- skip: start if(not run_real_web_requests) -->
            ```python
            >>> from pysmo import MiniStation
            >>> from pysmo.classes import StationXML
            >>> station = MiniStation(
            ...     name="ANMO", network="IU", location="00", channel="BHZ",
            ...     latitude=34.945981, longitude=-106.457133,
            ... )
            >>> epoch = StationXML.fetch(station=station)
            >>> epoch.has_response
            True
            >>>
            ```
            <!-- skip: end -->
        """
        epoch = cls.from_bytes(fetch_stationxml(station=station), time=time)
        if not epoch.has_response:
            raise ValueError(
                "fetched StationXML at level=response but it carried no "
                "<Response> element."
            )
        return epoch

    @classmethod
    def _from_raw(cls, raw: _RawStationEpoch) -> Self:
        response = None
        if raw.response is not None:
            response = MiniStagedResponse(
                poles=raw.response.poles,
                zeros=raw.response.zeros,
                overall_sensitivity=(
                    raw.response.normalization_factor * raw.response.sensitivity_value
                ),
                reference_sensitivity=raw.response.sensitivity_value,
                input_units=raw.response.sensitivity_input_units,
                stages=[
                    MiniResponseStage(
                        input_sample_rate=stage.input_sample_rate,
                        decimation_factor=stage.decimation_factor,
                        numerator=stage.numerator,
                        denominator=stage.denominator,
                        correction=stage.correction,
                    )
                    for stage in raw.response.digital_stages
                ],
            )
        return cls(
            network=raw.network,
            name=raw.station,
            location=raw.location,
            channel=raw.channel,
            latitude=raw.latitude,
            longitude=raw.longitude,
            elevation=raw.elevation,
            start_date=raw.start_date,
            end_date=raw.end_date,
            response=response,
        )


_Nslc = tuple[str, str, str, str]


def resolve_epochs(
    epochs: Iterable[StationXML], time: pd.Timestamp
) -> list[StationXML]:
    """Collapse station epochs to the one per NSLC valid at a given time.

    Groups `epochs` by network/station/location/channel and, within each
    group, keeps the single epoch whose `[start_date, end_date)` window
    covers `time` (an epoch with no `end_date` is still open and covers any
    time at or after its `start_date`). An NSLC with no covering epoch is
    dropped — that station provably was not recording then.

    Args:
        epochs: Station epochs, e.g. from
            [`StationXML.all_from_bytes`][pysmo.classes.StationXML.all_from_bytes].
        time: The time each NSLC's metadata is resolved at (UTC).

    Returns:
        One `StationXML` per NSLC that has a covering epoch, in first-seen
        NSLC order.

    Raises:
        ValueError: If an NSLC has more than one epoch covering `time`
            (overlapping validity windows — an invalid inventory).
    """
    time = convert_to_utc_timestamp(time)
    grouped: dict[_Nslc, list[StationXML]] = defaultdict(list)
    for epoch in epochs:
        grouped[(epoch.network, epoch.name, epoch.location, epoch.channel)].append(
            epoch
        )

    resolved: list[StationXML] = []
    for nslc, group in grouped.items():
        covering = [
            epoch
            for epoch in group
            if epoch.start_date <= time
            and (epoch.end_date is None or time < epoch.end_date)
        ]
        if not covering:
            continue
        if len(covering) > 1:
            raise ValueError(
                f"{'.'.join(nslc)} has {len(covering)} epochs covering {time}."
            )
        resolved.append(covering[0])
    return resolved
