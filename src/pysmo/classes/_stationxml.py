"""FDSN StationXML import class compatible with pysmo types."""

from typing import Self

import pandas as pd
from attrs import define, field, validators

from pysmo import MiniResponseStage, ResponseStage, Station
from pysmo.lib.io._stationxml import _RawResponse, parse_stationxml
from pysmo.lib.validators import convert_to_utc_timestamp, validate_nonzero
from pysmo.tools.web import fetch_stationxml
from pysmo.typing import NonZeroNumber

__all__ = ["StationXML"]


def _convert_optional_float(value: float | None) -> float | None:
    """Convert `value` to `float`, passing `None` through unchanged."""
    return None if value is None else float(value)


def _matching_epochs(
    epochs: list[_RawResponse],
    time: pd.Timestamp | None,
    *,
    location: str | None = None,
    channel: str | None = None,
) -> list[_RawResponse]:
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


@define(kw_only=True, slots=True)
class StationXML:
    """Import class for FDSN StationXML response metadata.

    Reads an instrument response from a
    [FDSN StationXML](http://www.fdsn.org/xml/station/) document (as
    returned by e.g. the EarthScope station web service with
    `level=response`) and exposes it as a
    [`Response`][pysmo.Response]-compatible object. Unlike
    [`SacPZ`][pysmo.classes.SacPZ], `StationXML` always satisfies
    [`StagedResponse`][pysmo.StagedResponse] too — `stages` is simply empty
    if the document has no digital FIR/IIR decimation stages.

    A StationXML document commonly covers a channel's full instrument
    history, i.e. several response epochs (e.g. after a sensor swap).
    [`from_bytes`][pysmo.classes.StationXML.from_bytes] narrows this to a
    single epoch (matching a given time, or the currently-open one);
    [`all_from_bytes`][pysmo.classes.StationXML.all_from_bytes] returns
    every epoch found, for callers who want to do their own selection.

    Examples:
        ```python
        >>> from pysmo import Response, StagedResponse
        >>> from pysmo.classes import StationXML
        >>> xml = b'''\\
        ... <?xml version="1.0"?>
        ... <FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
        ...   <Network code="IU">
        ...     <Station code="ANMO">
        ...       <Channel code="BHZ" locationCode="00"
        ...                startDate="2018-07-09T20:45:00.0000">
        ...         <Response>
        ...           <InstrumentSensitivity>
        ...             <Value>1.98475E9</Value>
        ...             <Frequency>0.02</Frequency>
        ...             <InputUnits><Name>m/s</Name></InputUnits>
        ...             <OutputUnits><Name>counts</Name></OutputUnits>
        ...           </InstrumentSensitivity>
        ...           <Stage number="1">
        ...             <PolesZeros>
        ...               <InputUnits><Name>m/s</Name></InputUnits>
        ...               <OutputUnits><Name>V</Name></OutputUnits>
        ...               <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
        ...               <NormalizationFactor>5.03773E14</NormalizationFactor>
        ...               <NormalizationFrequency>0.02</NormalizationFrequency>
        ...               <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
        ...               <Pole number="0"><Real>-0.037</Real><Imaginary>0.037</Imaginary></Pole>
        ...             </PolesZeros>
        ...             <Decimation>
        ...               <InputSampleRate>40.0</InputSampleRate>
        ...               <Factor>1</Factor>
        ...             </Decimation>
        ...             <StageGain><Value>1183.0</Value><Frequency>0.02</Frequency></StageGain>
        ...           </Stage>
        ...         </Response>
        ...       </Channel>
        ...     </Station>
        ...   </Network>
        ... </FDSNStationXML>'''
        >>> response = StationXML.from_bytes(xml)
        >>> isinstance(response, Response)
        True
        >>> isinstance(response, StagedResponse)
        True
        >>> response.network, response.station
        ('IU', 'ANMO')
        >>>
        ```
    """

    poles: list[complex] = field()
    """Response poles.

    See [`Response.poles`][pysmo.Response.poles] for more details.
    """

    zeros: list[complex] = field()
    """Response zeros.

    See [`Response.zeros`][pysmo.Response.zeros] for more details.
    """

    overall_sensitivity: NonZeroNumber = field(
        converter=float, validator=validate_nonzero
    )
    """Scale factor combined with `poles`/`zeros` to reconstruct `H(f)`
    (`NormalizationFactor * InstrumentSensitivity`).

    See [`Response.overall_sensitivity`][pysmo.Response.overall_sensitivity]
    for more details.
    """

    reference_sensitivity: NonZeroNumber | None = field(
        default=None,
        converter=_convert_optional_float,
        validator=validators.optional(validate_nonzero),
    )
    """Total system sensitivity at the reference frequency, `A0` excluded
    (StationXML's `InstrumentSensitivity/Value`).

    See
    [`Response.reference_sensitivity`][pysmo.Response.reference_sensitivity]
    for more details.
    """

    input_units: str = field(validator=validators.instance_of(str))
    """Physical units produced by removing this response.

    See [`Response.input_units`][pysmo.Response.input_units] for more details.
    """

    stages: list[ResponseStage] = field(factory=list)
    """Digital decimation stages, in signal order. Empty if the document has
    no digital stages.

    See [`StagedResponse.stages`][pysmo.StagedResponse.stages] for more details.
    """

    network: str = field(validator=validators.instance_of(str))
    """Network code parsed from the StationXML document."""

    station: str = field(validator=validators.instance_of(str))
    """Station code parsed from the StationXML document."""

    location: str = field(validator=validators.instance_of(str))
    """Location code parsed from the StationXML document."""

    channel: str = field(validator=validators.instance_of(str))
    """Channel code parsed from the StationXML document."""

    start_date: pd.Timestamp = field()
    """Start of the epoch this response applies to."""

    end_date: pd.Timestamp | None = field(default=None)
    """End of the epoch this response applies to, or `None` if still open."""

    @classmethod
    def from_bytes(
        cls,
        xml: bytes,
        *,
        time: pd.Timestamp | None = None,
        location: str | None = None,
        channel: str | None = None,
    ) -> Self:
        """Create a new instance from a StationXML document, selecting one epoch.

        A document is not guaranteed to cover a single channel — a
        station-level query (or one saved for later, offline use) commonly
        returns every location/channel combination on record, each with its
        own epoch history. `location`/`channel` narrow to one before `time`
        is applied; without them, a multi-channel document raises the same
        "more than one epoch" error as an ambiguous *time*.

        Args:
            xml: Raw StationXML document bytes (as returned by the FDSN
                station web service with `level=response`).
            time: Timestamp used to select the response epoch. If `None`,
                the currently-open epoch (no end date) is selected.
            location: Location code to narrow to, if `xml` covers more than
                one location. If `None`, location is not filtered.
            channel: Channel code to narrow to, if `xml` covers more than
                one channel. If `None`, channel is not filtered.

        Returns:
            A new StationXML instance for the response epoch active at
            *time* (or currently open, if `time` is `None`).

        Raises:
            ValueError: If, after narrowing by `location`/`channel`, zero or
                more than one response epoch matches *time* (or "currently
                open", if `time` is `None`).

        Tip: See Also
            [`StationXML.all_from_bytes`][pysmo.classes.StationXML.all_from_bytes]:
            Parse every epoch in the document without narrowing to one.
        """
        epochs = parse_stationxml(xml)
        matches = _matching_epochs(epochs, time, location=location, channel=channel)
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one response epoch in the given "
                f"StationXML at "
                f"{'the currently open epoch' if time is None else time}"
                f"{f', location {location!r}' if location is not None else ''}"
                f"{f', channel {channel!r}' if channel is not None else ''}, "
                f"found {len(matches)}."
            )
        return cls._from_raw(matches[0])

    @classmethod
    def fetch(cls, *, station: Station, time: pd.Timestamp | None = None) -> Self:
        """Fetch and parse an instrument response from the EarthScope FDSN
        station web service, selecting one epoch.

        A channel's instrument response usually has several epochs (e.g.
        after a sensor swap), so the request is narrowed to a single one:
        the epoch active at *time* if given, otherwise the one currently
        open (no `endDate`). Fetches the full response history in one
        request and narrows client-side (like
        [`from_bytes`][pysmo.classes.StationXML.from_bytes]); to fetch once
        and interpret later (e.g. offline, or without repeating the network
        request), use [`pysmo.tools.web.fetch_stationxml`][] and
        [`from_bytes`][pysmo.classes.StationXML.from_bytes] /
        [`all_from_bytes`][pysmo.classes.StationXML.all_from_bytes] directly
        instead.

        Args:
            station: Any object satisfying the [`Station`][pysmo.Station]
                protocol. Provides the network, station code, location, and
                channel for the request.
            time: Timestamp used to select the response epoch. If `None`,
                the currently-open epoch (no end date) is selected.

        Returns:
            A new StationXML instance for the response epoch active at
            *time* (or currently open, if `time` is `None`).

        Raises:
            ValueError: If zero or more than one response epoch matches
                *time* (or "currently open", if `time` is `None`).
            urllib3.exceptions.ResponseError: If the station web service
                returns an HTTP error.

        Examples:
            ```python
            >>> from pysmo import MiniStation
            >>> from pysmo.classes import StationXML
            >>> station = MiniStation(
            ...     name="ANMO", network="IU", location="00", channel="BHZ",
            ...     latitude=34.945981, longitude=-106.457133,
            ... )
            >>> response = StationXML.fetch(station=station)  # doctest: +SKIP
            >>>
            ```
        """
        xml = fetch_stationxml(station=station)
        return cls.from_bytes(xml, time=time)

    @classmethod
    def all_from_bytes(cls, xml: bytes) -> list[Self]:
        """Create one instance per response epoch in a StationXML document.

        Unlike [`from_bytes`][pysmo.classes.StationXML.from_bytes], this
        does not narrow to a single epoch — a document covering a channel's
        full instrument history returns several, each with its own
        `network`/`station`/`location`/`channel`/`start_date`/`end_date`
        provenance, which callers can filter themselves.

        Args:
            xml: Raw StationXML document bytes.

        Returns:
            One StationXML instance per response epoch found, in document
            order.
        """
        return [cls._from_raw(raw) for raw in parse_stationxml(xml)]

    @classmethod
    def _from_raw(cls, raw: _RawResponse) -> Self:
        return cls(
            poles=raw.poles,
            zeros=raw.zeros,
            overall_sensitivity=raw.normalization_factor * raw.sensitivity_value,
            reference_sensitivity=raw.sensitivity_value,
            input_units=raw.sensitivity_input_units,
            stages=[
                MiniResponseStage(
                    input_sample_rate=stage.input_sample_rate,
                    decimation_factor=stage.decimation_factor,
                    numerator=stage.numerator,
                    denominator=stage.denominator,
                    correction=stage.correction,
                )
                for stage in raw.digital_stages
            ],
            network=raw.network,
            station=raw.station,
            location=raw.location,
            channel=raw.channel,
            start_date=raw.start_date,
            end_date=raw.end_date,
        )
