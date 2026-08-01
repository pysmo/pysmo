"""SAC PZ (pole-zero) import class compatible with pysmo types."""

from typing import Self

import pandas as pd
from attrs import define, field, validators

from pysmo import Station
from pysmo.lib.io._sacpz import _RawSacPzResponse, parse_sacpz
from pysmo.lib.validators import validate_nonzero
from pysmo.tools.web import fetch_sacpz
from pysmo.typing import NonZeroNumber

__all__ = ["SacPZ"]


def _convert_optional_float(value: float | None) -> float | None:
    """Convert `value` to `float`, passing `None` through unchanged."""
    return None if value is None else float(value)


@define(kw_only=True, slots=True)
class SacPZ:
    """Import class for SAC PZ (pole-zero) files.

    Reads an analog instrument response from a
    [SAC PZ](https://ds.iris.edu/files/sac-manual/commands/transfer.html)
    file (as produced by e.g. the EarthScope SACPZ web service) and exposes
    it as a [`Response`][pysmo.Response]-compatible object. `SacPZ` only ever
    satisfies [`Response`][pysmo.Response], never
    [`StagedResponse`][pysmo.StagedResponse] — the SAC PZ format has no
    digital-stage fields to parse.

    Examples:
        ```python
        >>> from pysmo import Response
        >>> from pysmo.classes import SacPZ
        >>> text = '''\\
        ... * NETWORK   (KNETWK): IU
        ... * STATION    (KSTNM): ANMO
        ... * LOCATION   (KHOLE): 00
        ... * CHANNEL   (KCMPNM): BHZ
        ... * START             : 2018-07-09T20:45:00
        ... * END               :
        ... * INPUT UNIT        : M
        ... ZEROS 2
        ... \\t+0.000000e+00\\t+0.000000e+00
        ... \\t+0.000000e+00\\t+0.000000e+00
        ... POLES 1
        ... \\t-1.000000e-02\\t+0.000000e+00
        ... CONSTANT 1.0e+09
        ... '''
        >>> response = SacPZ.from_text(text)
        >>> isinstance(response, Response)
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
    """Total system sensitivity (the SAC PZ file's `CONSTANT`).

    See [`Response.overall_sensitivity`][pysmo.Response.overall_sensitivity]
    for more details.
    """

    reference_sensitivity: NonZeroNumber | None = field(
        default=None,
        converter=_convert_optional_float,
        validator=validators.optional(validate_nonzero),
    )
    """Total system sensitivity at the reference frequency, `A0` excluded
    (the SAC PZ file's `SENSITIVITY` header, if present).

    See
    [`Response.reference_sensitivity`][pysmo.Response.reference_sensitivity]
    for more details.
    """

    input_units: str = field(validator=validators.instance_of(str))
    """Physical units produced by removing this response via full spectral
    deconvolution — not necessarily via the sensitivity-only path, see
    [`remove_response`][pysmo.tools.signal.remove_response] for why.

    See [`Response.input_units`][pysmo.Response.input_units] for more details.
    """

    network: str = field(validator=validators.instance_of(str))
    """Network code parsed from the SAC PZ file's comment header."""

    station: str = field(validator=validators.instance_of(str))
    """Station code parsed from the SAC PZ file's comment header."""

    location: str = field(validator=validators.instance_of(str))
    """Location code parsed from the SAC PZ file's comment header."""

    channel: str = field(validator=validators.instance_of(str))
    """Channel code parsed from the SAC PZ file's comment header."""

    start_date: pd.Timestamp = field()
    """Start of the epoch this response applies to."""

    end_date: pd.Timestamp | None = field(default=None)
    """End of the epoch this response applies to, or `None` if still open."""

    @classmethod
    def from_text(cls, text: str) -> Self:
        """Create a new instance from a single-record SAC PZ text body.

        Args:
            text: SAC PZ text containing exactly one record (the common
                sidecar-file case, e.g. one `.pz`/`SACPZ.NET.STA.LOC.CHA`
                file matched to one channel epoch by filename convention).

        Returns:
            A new SacPZ instance.

        Raises:
            ValueError: If the text contains zero or more than one SAC PZ
                record.

        Tip: See Also
            [`SacPZ.all_from_text`][pysmo.classes.SacPZ.all_from_text]: Parse
            a bulk/concatenated multi-record text body.

        Examples:
            Reading a SAC PZ file already saved to disk — the common case for
            archived/legacy data, e.g. extracted from an old SEED volume with
            `rdseed -p`, rather than fetched live from EarthScope:

            ```python
            >>> from pathlib import Path
            >>> from pysmo import Response
            >>> from pysmo.classes import SacPZ
            >>> text = Path("SACPZ.IU.ANMO.00.BHZ").read_text()
            >>> response = SacPZ.from_text(text)
            >>> isinstance(response, Response)
            True
            >>> response.network, response.station
            ('IU', 'ANMO')
            >>>
            ```
        """
        records = parse_sacpz(text)
        if len(records) != 1:
            raise ValueError(
                f"Expected exactly one SAC PZ record in text, found {len(records)}."
            )
        return cls._from_raw(records[0])

    @classmethod
    def fetch(cls, *, station: Station, time: pd.Timestamp | None = None) -> Self:
        """Fetch and parse an instrument response from the EarthScope SACPZ
        web service, selecting one epoch.

        Unlike [`StationXML.fetch`][pysmo.classes.StationXML.fetch], epoch
        selection happens server-side: the SACPZ web service's own `time`
        parameter is passed through, so exactly one record is returned
        (the epoch active at *time* if given, otherwise the one currently
        open) without needing to fetch the full response history first.

        Args:
            station: Any object satisfying the [`Station`][pysmo.Station]
                protocol. Provides the network, station code, location, and
                channel for the request.
            time: Timestamp used to select the response epoch. If `None`,
                the currently-open epoch is selected.

        Returns:
            A new SacPZ instance for the response epoch active at *time*
            (or currently open, if `time` is `None`).

        Raises:
            ValueError: If the web service's response does not contain
                exactly one SAC PZ record.
            urllib3.exceptions.ResponseError: If the web service returns an
                HTTP error.

        Tip:
            When fetching live from EarthScope rather than reading an
            existing SAC PZ file, prefer
            [`StationXML.fetch`][pysmo.classes.StationXML.fetch]: the
            StationXML response also captures digital FIR/IIR stages, so it
            always satisfies [`StagedResponse`][pysmo.StagedResponse], unlike
            `SacPZ`.

        Examples:
            ```python
            >>> from pysmo import MiniStation
            >>> from pysmo.classes import SacPZ
            >>> station = MiniStation(
            ...     name="ANMO", network="IU", location="00", channel="BHZ",
            ...     latitude=34.945981, longitude=-106.457133,
            ... )
            >>> response = SacPZ.fetch(station=station)  # doctest: +SKIP
            >>>
            ```
        """
        text = fetch_sacpz(station=station, time=time)
        return cls.from_text(text)

    @classmethod
    def all_from_text(cls, text: str) -> list[Self]:
        """Create one instance per record in a bulk/concatenated SAC PZ text body.

        Unlike [`from_text`][pysmo.classes.SacPZ.from_text], this does not
        require (or merge to) a single record — a SACPZ retrieval that is
        not pinned to a single channel epoch returns multiple concatenated
        records, each with its own `network`/`station`/`location`/`channel`/
        `start_date`/`end_date` provenance, which callers can filter
        themselves.

        Args:
            text: SAC PZ text containing one or more records.

        Returns:
            One SacPZ instance per record found, in order of appearance.
        """
        return [cls._from_raw(record) for record in parse_sacpz(text)]

    @classmethod
    def _from_raw(cls, record: _RawSacPzResponse) -> Self:
        return cls(
            poles=record.poles,
            zeros=record.zeros,
            overall_sensitivity=record.overall_sensitivity,
            reference_sensitivity=record.reference_sensitivity,
            input_units=record.input_units,
            network=record.network,
            station=record.station,
            location=record.location,
            channel=record.channel,
            start_date=record.start_date,
            end_date=record.end_date,
        )
