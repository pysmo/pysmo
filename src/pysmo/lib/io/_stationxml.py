"""Low-level parsing of the FDSN StationXML format.

[`parse_stationxml`][pysmo.lib.io.parse_stationxml] walks a
[FDSN StationXML](http://www.fdsn.org/xml/station/) document once and returns
one uninterpreted `_RawStationEpoch` per `<Channel>` epoch (or per
`<Station>` for a channel-less `level=station` document): NSLC identity,
coordinates, the validity window, and — when the document carried one — the
instrument `_RawResponse`. Interpretation into a
[`Station`][pysmo.Station]-compatible object with a nested response happens
one layer up, in [`pysmo.classes.StationXML`][].
"""

import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = ["parse_stationxml"]

_NS = {"fdsn": "http://www.fdsn.org/xml/station/1"}


_ANALOG_PZ_TYPE = "LAPLACE (RADIANS/SECOND)"
"""The only `PzTransferFunctionType` supported for the analog stage."""

_DIGITAL_CF_TYPE = "DIGITAL"
"""The only `CfTransferFunctionType` supported for a `<Coefficients>` stage.

`<Coefficients>` can also encode an `ANALOG (RADIANS/SECOND)` or `ANALOG
(HERTZ)` s-domain rational function; only `DIGITAL` (z-domain) belongs in
`_RawDigitalStage`, which is evaluated with `scipy.signal.freqz`."""


@dataclass
class _RawDigitalStage:
    """A single uninterpreted digital (FIR/IIR) decimation stage."""

    input_sample_rate: float
    decimation_factor: int
    numerator: list[float] = field(default_factory=list)
    denominator: list[float] = field(default_factory=lambda: [1.0])
    correction: float = 0.0


@dataclass
class _RawResponse:
    """A single uninterpreted instrument response (no channel/epoch identity)."""

    poles: list[complex]
    zeros: list[complex]
    normalization_factor: float
    sensitivity_value: float
    sensitivity_input_units: str
    digital_stages: list[_RawDigitalStage] = field(default_factory=list)


@dataclass
class _RawStationEpoch:
    """One uninterpreted `<Channel>` (or channel-less `<Station>`) epoch."""

    network: str
    station: str
    location: str
    channel: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp | None
    latitude: float
    longitude: float
    elevation: float | None
    response: _RawResponse | None


def _parse_timestamp(value: str | None) -> pd.Timestamp | None:
    """Parse an XML attribute string to a UTC timestamp, or `None` if absent."""
    if value is None:
        return None
    return convert_to_utc_timestamp(value)


def _child_text(elem: ET.Element, tag: str) -> str:
    """Return `elem`'s required `<tag>` child's text, raising if absent."""
    child = elem.find(f"fdsn:{tag}", _NS)
    if child is None or child.text is None:
        raise ValueError(f"Missing required <{tag}> element.")
    return child.text


def _optional_child_float(elem: ET.Element, tag: str) -> float | None:
    """Return `elem`'s `<tag>` child as a float, or `None` if absent/empty."""
    child = elem.find(f"fdsn:{tag}", _NS)
    if child is None or child.text is None or not child.text.strip():
        return None
    return float(child.text)


def _parse_pz_values(pz: ET.Element, tag: str) -> list[complex]:
    """Parse a `PolesZeros` element's `<tag>` entries into complex values.

    Args:
        pz: `<PolesZeros>` element to read entries from.
        tag: Entry element name to look up (`"Zero"` or `"Pole"`), sorted by
            their `number` attribute.
    """
    entries = sorted(
        pz.findall(f"fdsn:{tag}", _NS), key=lambda e: int(e.get("number", 0))
    )
    return [
        complex(
            float(_child_text(entry, "Real")), float(_child_text(entry, "Imaginary"))
        )
        for entry in entries
    ]


def _parse_coefficients(
    elem: ET.Element, tag: str, index_attr: str = "number"
) -> list[float]:
    """Parse an element's `<tag>` entries into floats, sorted by `index_attr`.

    Args:
        elem: Element to read `<tag>` entries from.
        tag: Entry element name to look up (`"Numerator"`, `"Denominator"`
            or `"NumeratorCoefficient"`).
        index_attr: Attribute each entry is indexed/sorted by. FDSN
            StationXML is inconsistent here: `<Numerator>`/`<Denominator>`
            (under `<Coefficients>`) use `"number"`, but `<NumeratorCoefficient>`
            (under `<FIR>`) uses `"i"` instead.
    """
    entries = sorted(
        elem.findall(f"fdsn:{tag}", _NS), key=lambda e: int(e.get(index_attr, 0))
    )
    return [float(entry.text) for entry in entries if entry.text is not None]


def _expand_fir_symmetry(coefficients: list[float], symmetry: str) -> list[float]:
    """Expand FDSN's symmetric-FIR shorthand into the full coefficient list.

    `NONE` coefficients are already complete. `ODD` symmetry lists the first
    half plus a shared centre tap; mirroring all but that last (centre) value
    gives the full, odd-length filter. `EVEN` symmetry lists exactly half,
    with no shared centre tap; mirroring the full list gives the even-length
    filter. See the FDSN StationXML docs' FIR element for the worked
    examples this mirrors: `ODD` `[0.1, 0.4, 0.5]` -> `[0.1, 0.4, 0.5, 0.4,
    0.1]`; `EVEN` `[0.1, 0.4, 0.5]` -> `[0.1, 0.4, 0.5, 0.5, 0.4, 0.1]`.
    """
    if symmetry == "NONE":
        return coefficients
    if symmetry == "ODD":
        return coefficients + coefficients[-2::-1]
    if symmetry == "EVEN":
        return coefficients + coefficients[::-1]
    raise ValueError(
        f"Unsupported FIR Symmetry {symmetry!r}; expected 'NONE', 'ODD' or 'EVEN'."
    )


def _normalise_unit_gain(
    numerator: list[float], denominator: list[float]
) -> list[float]:
    """Scale `numerator` so the stage has unit gain at DC (`z = 1`).

    Assumes the stage's own `StageGain/Frequency` is 0 Hz (the normal case
    for a decimation stage; not independently checked here) — the
    `StageGain/Value` itself is discarded regardless, since
    `InstrumentSensitivity` already carries the end-to-end system gain.

    Raises `ValueError` if `numerator` sums to zero, which is correct for
    the decimation FIR/IIR stages this module targets (unit-gain by design)
    but would also reject a deliberately zero-DC-gain stage (e.g. a
    differentiator-style FIR) — not something the FDSN decimation stages
    handled here are expected to encode.
    """
    numerator_sum = sum(numerator)
    if numerator_sum == 0:
        raise ValueError(
            "Cannot normalise a digital stage whose coefficients sum to 0."
        )
    scale = sum(denominator) / numerator_sum
    return [value * scale for value in numerator]


def _parse_decimation(stage: ET.Element) -> tuple[float, int, float]:
    """Parse `stage`'s `<Decimation>` element into `(input_sample_rate, decimation_factor, correction)`; `correction` defaults to `0.0` if `<Correction>` is absent."""
    decimation = stage.find("fdsn:Decimation", _NS)
    if decimation is None:
        raise ValueError(f"Stage {stage.get('number')} has no <Decimation> element.")
    input_sample_rate = float(_child_text(decimation, "InputSampleRate"))
    factor_text = _child_text(decimation, "Factor")
    factor = float(factor_text)
    if not factor.is_integer():
        raise ValueError(
            f"Stage {stage.get('number')}'s <Decimation>/<Factor> "
            f"{factor_text!r} is not a whole number."
        )
    decimation_factor = int(factor)
    # <Offset> (which input sample the decimated output is aligned to) has no
    # effect on the frequency response and is not read.
    #
    # <Delay> (the filter's own nominal/estimated delay) is also not read:
    # only <Correction> (what was actually applied to the recorded samples)
    # matters for reconstructing the recorded data's transfer function —
    # matching evalresp's default behaviour of using correction_applied
    # rather than estimated_delay.
    correction_elem = decimation.find("fdsn:Correction", _NS)
    correction = (
        float(correction_elem.text)
        if correction_elem is not None and correction_elem.text is not None
        else 0.0
    )
    if correction < 0:
        warnings.warn(
            f"Stage {stage.get('number')} has a negative <Correction> "
            f"({correction}s). Correction is almost always >= 0 (it "
            "cancels the stage's own, almost-always-positive <Delay>); a "
            "negative value more likely indicates a metadata error at the "
            "provider than a genuine non-causal correction, and will "
            "shift timing the wrong way if used as-is.",
            UserWarning,
            stacklevel=2,
        )
    return input_sample_rate, decimation_factor, correction


_AnalogPayload = tuple[list[complex], list[complex], float]
"""An analog stage's `(poles, zeros, normalization_factor)`."""

_StageParseResult = (
    tuple[Literal["analog"], _AnalogPayload]
    | tuple[Literal["digital"], _RawDigitalStage]
    | tuple[Literal["gain"], None]
)
"""`_parse_stage`'s tagged-union result."""


def _parse_stage(stage: ET.Element) -> _StageParseResult:
    """Parse one `<Stage>` element into `("analog" | "digital" | "gain", payload)`."""
    pz = stage.find("fdsn:PolesZeros", _NS)
    if pz is not None:
        pz_type = _child_text(pz, "PzTransferFunctionType")
        if pz_type != _ANALOG_PZ_TYPE:
            raise ValueError(
                f"Unsupported PzTransferFunctionType {pz_type!r} in stage "
                f"{stage.get('number')}; only {_ANALOG_PZ_TYPE!r} is supported."
            )
        normalization_factor = float(_child_text(pz, "NormalizationFactor"))
        # <NormalizationFrequency> (the frequency NormalizationFactor is
        # calibrated at) isn't needed: normalization_factor alone fixes the
        # transfer function's gain everywhere.
        zeros = _parse_pz_values(pz, "Zero")
        poles = _parse_pz_values(pz, "Pole")
        return "analog", (poles, zeros, normalization_factor)

    coefficients = stage.find("fdsn:Coefficients", _NS)
    fir = stage.find("fdsn:FIR", _NS)
    if coefficients is not None:
        cf_type = _child_text(coefficients, "CfTransferFunctionType")
        if cf_type != _DIGITAL_CF_TYPE:
            raise ValueError(
                f"Unsupported CfTransferFunctionType {cf_type!r} in stage "
                f"{stage.get('number')}; only {_DIGITAL_CF_TYPE!r} is "
                "supported."
            )
        input_sample_rate, decimation_factor, correction = _parse_decimation(stage)
        numerator = _parse_coefficients(coefficients, "Numerator")
        denominator = _parse_coefficients(coefficients, "Denominator")
        if numerator or denominator:
            denominator = denominator or [1.0]
            numerator = _normalise_unit_gain(numerator, denominator)
        else:
            # No coefficients at all: a pure scalar-gain "stage" (e.g. an
            # ADC gain conversion) rather than an actual filter. Its
            # StageGain is discarded anyway (see MiniResponseStage's
            # unit-gain-by-construction convention), so this is a harmless
            # identity stage, not a divide-by-zero when normalising.
            numerator, denominator = [1.0], [1.0]
        return "digital", _RawDigitalStage(
            input_sample_rate=input_sample_rate,
            decimation_factor=decimation_factor,
            numerator=numerator,
            denominator=denominator,
            correction=correction,
        )
    if fir is not None:
        input_sample_rate, decimation_factor, correction = _parse_decimation(stage)
        numerator = _parse_coefficients(fir, "NumeratorCoefficient", index_attr="i")
        denominator = [1.0]
        if numerator:
            symmetry = _child_text(fir, "Symmetry")
            numerator = _expand_fir_symmetry(numerator, symmetry)
            numerator = _normalise_unit_gain(numerator, denominator)
        else:
            # No coefficients at all: same harmless scalar-gain identity
            # stage as the no-coefficients <Coefficients> case above.
            numerator = [1.0]
        return "digital", _RawDigitalStage(
            input_sample_rate=input_sample_rate,
            decimation_factor=decimation_factor,
            numerator=numerator,
            denominator=denominator,
            correction=correction,
        )

    if stage.find("fdsn:Decimation", _NS) is None:
        # No PolesZeros/Coefficients/FIR and no Decimation: a pure
        # scalar-gain stage (e.g. an analog amplifier between the sensor
        # and digitiser) with no frequency-dependent behaviour at all. Its
        # StageGain is discarded anyway (see MiniResponseStage's
        # unit-gain-by-construction convention, and InstrumentSensitivity
        # already reflects the end-to-end gain), so it is safe to skip
        # entirely rather than treat as an error.
        return "gain", None

    raise ValueError(
        f"Stage {stage.get('number')} has no recognised PolesZeros/Coefficients/"
        "FIR element."
    )


def _parse_response(response: ET.Element) -> _RawResponse:
    """Parse a `<Response>` element into a `_RawResponse`."""
    sensitivity = response.find("fdsn:InstrumentSensitivity", _NS)
    if sensitivity is None:
        raise ValueError("Response has no <InstrumentSensitivity> element.")
    sensitivity_value = float(_child_text(sensitivity, "Value"))
    input_units = sensitivity.find("fdsn:InputUnits", _NS)
    if input_units is None:
        raise ValueError("InstrumentSensitivity has no <InputUnits> element.")
    sensitivity_input_units = _child_text(input_units, "Name")

    poles: list[complex] = []
    zeros: list[complex] = []
    normalization_factor: float | None = None
    digital_stages: list[_RawDigitalStage] = []

    # The <Stage number="..."> attribute — not document order — is the
    # authoritative processing sequence (FDSN StationXML schema: "Start from
    # name='1' and iterate sequentially"); a producer is free to emit stages
    # out of order.
    stages = sorted(
        response.findall("fdsn:Stage", _NS),
        key=lambda stage: int(stage.get("number", 0)),
    )
    for stage in stages:
        match _parse_stage(stage):
            case ("analog", (parsed_poles, parsed_zeros, parsed_normalization_factor)):
                # Cascaded analog stages (e.g. a sensor followed by an
                # analog preamplifier encoded per FDSN convention as a
                # gain-only PolesZeros stage) multiply in the s-domain:
                # their poles/zeros concatenate and normalisation factors
                # multiply together.
                poles += parsed_poles
                zeros += parsed_zeros
                normalization_factor = (
                    parsed_normalization_factor
                    if normalization_factor is None
                    else normalization_factor * parsed_normalization_factor
                )
            case ("digital", digital_stage):
                digital_stages.append(digital_stage)
            case ("gain", None):
                # A pure scalar-gain stage, already folded into
                # InstrumentSensitivity — nothing to record.
                pass

    if normalization_factor is None:
        raise ValueError("Response has no analog PolesZeros stage.")

    return _RawResponse(
        poles=poles,
        zeros=zeros,
        normalization_factor=normalization_factor,
        sensitivity_value=sensitivity_value,
        sensitivity_input_units=sensitivity_input_units,
        digital_stages=digital_stages,
    )


def _epoch_coords(
    elem: ET.Element, fallback: tuple[float | None, float | None, float | None]
) -> tuple[float | None, float | None, float | None]:
    """Return `elem`'s lat/lon/elevation, each falling back to `fallback` when absent."""
    latitude = _optional_child_float(elem, "Latitude")
    longitude = _optional_child_float(elem, "Longitude")
    elevation = _optional_child_float(elem, "Elevation")
    return (
        fallback[0] if latitude is None else latitude,
        fallback[1] if longitude is None else longitude,
        fallback[2] if elevation is None else elevation,
    )


def parse_stationxml(xml: bytes) -> list[_RawStationEpoch]:
    """Parse station identity, coordinates and response from a StationXML document.

    Walks the document once and returns one entry per `<Channel>` epoch (or
    per `<Station>` for a channel-less `level=station` document), in document
    order — the FDSN station web service does not default to a single
    "current" epoch, so a query covering a channel's full history returns
    several. Epoch *selection* is left to the caller. `<Response>` is read
    when present (`level=response`) and left as `None` otherwise;
    channel-level coordinates take precedence over station-level ones.

    Args:
        xml: Raw StationXML document bytes (any `level` that carries
            coordinates — `channel`, `station` or `response`).

    Returns:
        One uninterpreted epoch per `<Channel>` (or `<Station>`) found, in
        document order.

    Raises:
        ValueError: If `xml` is not well-formed XML, a `<Network>`,
            `<Station>` or `<Channel>` element has no `code` attribute, a
            `<Channel>` (or channel-less `<Station>`) has no `startDate`, an
            epoch has neither channel-level nor station-level
            latitude/longitude, or a `<Response>` that is present uses an
            unrecognised or unsupported encoding.

    Examples:
        ```python
        >>> from pysmo.lib.io._stationxml import parse_stationxml
        >>> xml = b'''<?xml version="1.0"?>
        ... <FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
        ...   <Network code="IU">
        ...     <Station code="ANMO">
        ...       <Latitude>34.9</Latitude><Longitude>-106.5</Longitude>
        ...       <Channel code="BHZ" locationCode="00"
        ...                startDate="2018-07-09T20:45:00.0000">
        ...         <Latitude>34.95</Latitude><Longitude>-106.46</Longitude>
        ...         <Elevation>1632.7</Elevation>
        ...       </Channel>
        ...     </Station>
        ...   </Network>
        ... </FDSNStationXML>'''
        >>> epochs = parse_stationxml(xml)
        >>> len(epochs)
        1
        >>> epochs[0].station, epochs[0].channel, epochs[0].latitude
        ('ANMO', 'BHZ', 34.95)
        >>> epochs[0].response is None
        True
        >>>
        ```
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f"Not well-formed XML: {exc}") from exc

    results: list[_RawStationEpoch] = []
    for network_elem in root.findall("fdsn:Network", _NS):
        network_code = network_elem.get("code")
        if network_code is None:
            raise ValueError("<Network> element has no code attribute.")
        for station_elem in network_elem.findall("fdsn:Station", _NS):
            station_code = station_elem.get("code")
            if station_code is None:
                raise ValueError(
                    f"<Station> element in network {network_code!r} has no "
                    "code attribute."
                )
            station_coords = (
                _optional_child_float(station_elem, "Latitude"),
                _optional_child_float(station_elem, "Longitude"),
                _optional_child_float(station_elem, "Elevation"),
            )

            channels = station_elem.findall("fdsn:Channel", _NS)
            elements: list[tuple[ET.Element, str, str]] = (
                [(station_elem, "", "")]
                if not channels
                else [
                    (channel, channel.get("code", ""), channel.get("locationCode", ""))
                    for channel in channels
                ]
            )

            for elem, channel_code, location_code in elements:
                if channels and not channel_code:
                    raise ValueError(
                        f"<Channel> element in station "
                        f"{network_code}.{station_code} has no code attribute."
                    )
                start_date = _parse_timestamp(elem.get("startDate"))
                if start_date is None:
                    what = f"Channel {channel_code!r}" if channels else "Station"
                    raise ValueError(
                        f"{what} in station {network_code}.{station_code} has "
                        "no startDate attribute."
                    )
                latitude, longitude, elevation = _epoch_coords(elem, station_coords)
                if latitude is None or longitude is None:
                    raise ValueError(
                        f"{network_code}.{station_code}."
                        f"{channel_code or '(station)'} has no latitude/longitude."
                    )
                response_elem = elem.find("fdsn:Response", _NS)
                results.append(
                    _RawStationEpoch(
                        network=network_code,
                        station=station_code,
                        location=location_code,
                        channel=channel_code,
                        start_date=start_date,
                        end_date=_parse_timestamp(elem.get("endDate")),
                        latitude=latitude,
                        longitude=longitude,
                        elevation=elevation,
                        response=(
                            None
                            if response_elem is None
                            else _parse_response(response_elem)
                        ),
                    )
                )

    return results
