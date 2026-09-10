"""FDSN StationXML import class compatible with pysmo types."""

import warnings
from collections import defaultdict
from collections.abc import Iterable
from typing import Self

import pandas as pd
from attrs import converters, define, field, validators

from pysmo import MiniResponseStage, MiniStagedResponse, Station
from pysmo.lib.converters import to_longitude, to_utc_timestamp
from pysmo.lib.io._stationxml import _RawStationEpoch, parse_stationxml
from pysmo.lib.validators import is_latitude, is_longitude
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
        time = to_utc_timestamp(time)
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
    coordinates, the epoch's validity window, and (when the document was
    fetched at `level=response`) the instrument
    [`response`][pysmo.classes.StationXML.response].

    A document commonly covers a channel's full history, i.e. several
    epochs. [`from_bytes`][pysmo.classes.StationXML.from_bytes] narrows to
    one (matching a time, or the currently-open one);
    [`all_from_bytes`][pysmo.classes.StationXML.all_from_bytes] returns every
    epoch found. Accessing
    [`response`][pysmo.classes.StationXML.response] raises for an epoch
    parsed from a `level=channel` / `level=station` document (e.g. a bulk
    inventory fetched with
    [`pysmo.tools.web.fetch_station_inventory`][]); guard it with
    [`has_response`][pysmo.classes.StationXML.has_response].
    [`fetch`][pysmo.classes.StationXML.fetch] always populates it.

    Examples:
        ```python
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
        >>> station.network, station.name, station.channel
        ('IU', 'ANMO', 'BHZ')
        >>> station.response.input_units
        'm/s'
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

    latitude: float = field(converter=float, validator=is_latitude)
    """Latitude in degrees, -90 to 90."""

    longitude: float = field(converter=to_longitude, validator=is_longitude)
    """Longitude in degrees, -180 to 180 (-180 is stored as +180)."""

    elevation: float | None = field(default=None, converter=converters.optional(float))
    """Elevation in metres, or `None` if the document omits it."""

    start_date: pd.Timestamp = field(converter=to_utc_timestamp)
    """Start of this metadata epoch."""

    end_date: pd.Timestamp | None = field(
        default=None, converter=converters.optional(to_utc_timestamp)
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
                `<Response>`; check
                [`has_response`][pysmo.classes.StationXML.has_response]
                first, or fetch at `level=response`
                ([`StationXML.fetch`][pysmo.classes.StationXML.fetch]).
        """
        if self._response is None:
            raise ValueError(
                f"{self.network}.{self.name}.{self.location}.{self.channel} was "
                + "parsed from a document with no <Response>; fetch it at "
                + "level=response."
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
        strict: bool = True,
    ) -> Self:
        """Create a new instance from a StationXML document, selecting one epoch.

        A document is not guaranteed to cover a single channel: a bulk or
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
            strict: If `True` (default), any unrepresentable epoch in `xml`
                fails the call. If `False`, such epochs are skipped (with a
                `UserWarning`) before narrowing, so a bad *other* epoch
                doesn't block selecting the one asked for.

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
            parse_stationxml(xml, strict=strict),
            time,
            network=network,
            station=station,
            location=location,
            channel=channel,
        )
        if len(matches) != 1:
            raise ValueError(
                "Expected exactly one epoch in the given StationXML at "
                + f"{'the currently open epoch' if time is None else time}"
                + f"{f', network {network!r}' if network is not None else ''}"
                + f"{f', station {station!r}' if station is not None else ''}"
                + f"{f', location {location!r}' if location is not None else ''}"
                + f"{f', channel {channel!r}' if channel is not None else ''}, "
                + f"found {len(matches)}."
            )
        return cls._from_raw(matches[0])

    @classmethod
    def all_from_bytes(cls, xml: bytes, *, strict: bool = True) -> list[Self]:
        """Create one instance per `<Channel>` epoch in a StationXML document.

        Unlike [`from_bytes`][pysmo.classes.StationXML.from_bytes], this does
        not narrow: a document covering a channel's full history returns
        several, each with its own NSLC / `start_date` / `end_date`.

        Args:
            xml: Raw StationXML document bytes.
            strict: If `True` (default), a single unrepresentable epoch
                fails the whole parse. If `False`, unrepresentable epochs
                are skipped and a `UserWarning` reports how many — useful
                for a bulk `level=response` inventory where one channel's
                unsupported response encoding should not discard the rest.

        Returns:
            One StationXML instance per representable epoch, in document order.
        """
        return cls._instances_from_raw(
            parse_stationxml(xml, strict=strict), strict=strict
        )

    @classmethod
    def _instances_from_raw(
        cls, raws: list[_RawStationEpoch], *, strict: bool
    ) -> list[Self]:
        """Build instances from parsed epochs, applying the strictness boundary.

        `parse_stationxml` skips XML that will not parse; this skips an epoch
        that parses but fails `StationXML` or nested-response validation (an
        out-of-range coordinate, a zero sensitivity, an invalid digital stage).
        """
        instances: list[Self] = []
        skipped: list[str] = []
        for raw in raws:
            try:
                instances.append(cls._from_raw(raw))
            except (ValueError, TypeError) as error:
                if strict:
                    raise
                skipped.append(
                    f"{raw.network}.{raw.station}.{raw.location}.{raw.channel} "
                    + f"@ {raw.start_date} ({error})"
                )
        if skipped:
            warnings.warn(
                f"Skipped {len(skipped)} unrepresentable StationXML epoch(s); "
                + f"first: {skipped[0]}",
                UserWarning,
                stacklevel=3,
            )
        return instances

    @classmethod
    def fetch(cls, *, station: Station, time: pd.Timestamp | None = None) -> Self:
        """Fetch one channel's response epoch from EarthScope's FDSN station service.

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
                + "<Response> element."
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
    dropped; that station provably was not recording then.

    Args:
        epochs: Station epochs, e.g. from
            [`StationXML.all_from_bytes`][pysmo.classes.StationXML.all_from_bytes].
        time: The time each NSLC's metadata is resolved at (UTC).

    Returns:
        One `StationXML` per NSLC that has a covering epoch, in first-seen
        NSLC order.

    Raises:
        ValueError: If an NSLC has more than one epoch covering `time`
            (overlapping validity windows, i.e. an invalid inventory).
    """
    time = to_utc_timestamp(time)
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
