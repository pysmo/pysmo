"""Low-level parsing of the SAC PZ (pole-zero) text format.

A SAC PZ file (as produced by e.g. the EarthScope SACPZ web service) encodes
one instrument's analog response as poles, zeros, and a single `CONSTANT`
(the product of the analog normalisation factor `A0` and the overall system
sensitivity — see
[`Response.overall_sensitivity`][pysmo.Response.overall_sensitivity]). A text
body may contain several concatenated records (one per channel epoch); each
is introduced by a `* NETWORK`/`* STATION`/`* LOCATION`/`* CHANNEL`/
`* START`/`* END` comment header, plus an optional `* SENSITIVITY` header
giving the plain reference-frequency sensitivity with `A0` excluded (see
[`Response.reference_sensitivity`][pysmo.Response.reference_sensitivity]) —
present in real EarthScope output, but not guaranteed for hand-written SAC PZ
text.

[`parse_sacpz`][pysmo.lib.io._sacpz.parse_sacpz] splits a text body into raw,
uninterpreted [`_RawSacPzResponse`][pysmo.lib.io._sacpz._RawSacPzResponse]
records without constructing any `pysmo` type — mirroring the "parse, don't
interpret" split used by
[`parse_geocsv`][pysmo.lib.io.parse_geocsv] and
[`parse_stationxml`][pysmo.lib.io.parse_stationxml]. Interpretation into a
[`Response`][pysmo.Response]-compatible object happens one layer up, in
[`pysmo.classes.SacPZ`][].
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from os import PathLike
from typing import Protocol, runtime_checkable

import pandas as pd

from pysmo import EpochProvenance, Response
from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = ["parse_sacpz", "write_sacpz", "ResponseWithEpoch"]


@runtime_checkable
class ResponseWithEpoch(Response, EpochProvenance, Protocol):
    """Protocol class to define the `ResponseWithEpoch` type.

    A [`Response`][pysmo.Response] with
    [`EpochProvenance`][pysmo.EpochProvenance] — what
    [`write_sacpz`][pysmo.lib.io.write_sacpz] requires. Any object
    satisfying both protocols (e.g. [`SacPZ`][pysmo.classes.SacPZ] or
    [`StationXML`][pysmo.classes.StationXML]) already satisfies this one
    structurally; there is usually no need to reference it directly unless
    type-annotating a variable meant to hold whatever `write_sacpz` accepts.
    """


_HEADER_PATTERN = re.compile(
    r"^\*\s*([A-Za-z][A-Za-z ]*?)\s*(?:\([^)]*\))?\s*:\s*(.*?)\s*$"
)
"""A `* KEY (SACHDR): value` or `* KEY: value` comment header line."""

_REQUIRED_HEADERS = ("NETWORK", "STATION", "LOCATION", "CHANNEL", "START", "INPUT UNIT")


def _parse_float(value: str) -> float:
    """Convert `value` to `float`, tolerating Fortran `D`/`d` exponents."""
    return float(value.replace("D", "E").replace("d", "e"))


@dataclass
class _RawSacPzResponse:
    """A single uninterpreted SAC PZ record."""

    network: str
    station: str
    location: str
    channel: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp | None
    poles: list[complex]
    zeros: list[complex]
    overall_sensitivity: float
    reference_sensitivity: float | None
    input_units: str


def _parse_headers(lines: list[str], index: int) -> tuple[dict[str, str], int]:
    """Parse consecutive `* KEY: value` comment header lines starting at `index`."""
    headers: dict[str, str] = {}
    while index < len(lines) and lines[index].strip().startswith("*"):
        if match := _HEADER_PATTERN.match(lines[index]):
            headers[match.group(1).strip()] = match.group(2).strip()
        index += 1
    return headers, index


def _parse_complex_block(
    lines: list[str], index: int, keyword: str
) -> tuple[list[complex], int]:
    """Parse a `KEYWORD <count>` block of `real imag` pairs starting at `index`.

    Args:
        keyword: Block keyword expected at `lines[index]` (`"ZEROS"` or `"POLES"`).
    """
    stripped = lines[index].strip() if index < len(lines) else ""
    if not stripped.startswith(keyword):
        raise ValueError(
            f"Expected '{keyword}' block at line {index + 1}, found {stripped!r}."
        )
    count = int(stripped.split()[1])
    index += 1
    values: list[complex] = []
    for _ in range(count):
        if index >= len(lines):
            raise ValueError(f"Unexpected end of text while parsing '{keyword}' block.")
        real, imag = (_parse_float(part) for part in lines[index].split())
        values.append(complex(real, imag))
        index += 1
    return values, index


def parse_sacpz(text: str) -> list[_RawSacPzResponse]:
    """Split SAC PZ text into a list of uninterpreted records.

    A text body may contain several concatenated records (the EarthScope
    SACPZ web service returns one per channel epoch when a query is not
    pinned to a single epoch); this function returns all of them, in order
    of appearance.

    Args:
        text: SAC PZ text body, containing one or more records.

    Returns:
        List of uninterpreted SAC PZ records in order of appearance.

    Raises:
        ValueError: If a record is missing a required header field, or the
            `ZEROS`/`POLES`/`CONSTANT` blocks are missing or malformed.

    Examples:
        ```python
        >>> from pysmo.lib.io._sacpz import parse_sacpz
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
        >>> records = parse_sacpz(text)
        >>> len(records)
        1
        >>> records[0].network, records[0].station
        ('IU', 'ANMO')
        >>> records[0].end_date is None
        True
        >>>
        ```
    """
    lines = text.splitlines()
    records: list[_RawSacPzResponse] = []
    index = 0
    n = len(lines)

    while index < n:
        if not lines[index].strip():
            index += 1
            continue
        if not lines[index].strip().startswith("*"):
            raise ValueError(
                f"Expected a comment header line at line {index + 1}, found "
                f"{lines[index]!r}."
            )

        headers, index = _parse_headers(lines, index)
        missing = [key for key in _REQUIRED_HEADERS if key not in headers]
        if missing:
            raise ValueError(f"SAC PZ record is missing required header(s): {missing}.")

        zeros, index = _parse_complex_block(lines, index, "ZEROS")
        poles, index = _parse_complex_block(lines, index, "POLES")

        constant_line = lines[index].strip() if index < n else ""
        if not constant_line.startswith("CONSTANT"):
            raise ValueError(
                f"Expected 'CONSTANT' at line {index + 1}, found {constant_line!r}."
            )
        overall_sensitivity = _parse_float(constant_line.split()[1])
        index += 1

        end_date_text = headers.get("END", "")
        sensitivity_text = headers.get("SENSITIVITY", "")
        records.append(
            _RawSacPzResponse(
                network=headers["NETWORK"],
                station=headers["STATION"],
                location=headers["LOCATION"],
                channel=headers["CHANNEL"],
                start_date=convert_to_utc_timestamp(headers["START"]),
                end_date=(
                    convert_to_utc_timestamp(end_date_text) if end_date_text else None
                ),
                poles=poles,
                zeros=zeros,
                overall_sensitivity=overall_sensitivity,
                reference_sensitivity=(
                    _parse_float(sensitivity_text.split()[0])
                    if sensitivity_text
                    else None
                ),
                input_units=headers["INPUT UNIT"],
            )
        )

    return records


def _sacpz_block(response: ResponseWithEpoch) -> str:
    """Render a single Response+EpochProvenance object as one SAC PZ record."""
    end_date = response.end_date.isoformat() if response.end_date is not None else ""

    lines = [
        f"* NETWORK   (KNETWK): {response.network}",
        f"* STATION    (KSTNM): {response.station}",
        f"* LOCATION   (KHOLE): {response.location}",
        f"* CHANNEL   (KCMPNM): {response.channel}",
        f"* START             : {response.start_date.isoformat()}",
        f"* END               : {end_date}",
    ]
    if response.reference_sensitivity is not None:
        lines.append(f"* SENSITIVITY       : {response.reference_sensitivity:.6e}")
    lines.append(f"* INPUT UNIT        : {response.input_units}")

    lines.append(f"ZEROS {len(response.zeros)}")
    for zero in response.zeros:
        lines.append(f"\t{zero.real:+.6e}\t{zero.imag:+.6e}")

    lines.append(f"POLES {len(response.poles)}")
    for pole in response.poles:
        lines.append(f"\t{pole.real:+.6e}\t{pole.imag:+.6e}")

    lines.append(f"CONSTANT {response.overall_sensitivity:.6e}")

    return "\n".join(lines)


def write_sacpz(
    responses: ResponseWithEpoch | Sequence[ResponseWithEpoch],
    path: str | PathLike,
) -> None:
    """Write one or more Response objects to a SAC PZ file.

    Args:
        responses: A single object satisfying both
            [`Response`][pysmo.Response] and
            [`EpochProvenance`][pysmo.EpochProvenance] (e.g.
            [`SacPZ`][pysmo.classes.SacPZ] or
            [`StationXML`][pysmo.classes.StationXML]), or a non-empty
            sequence of them.
        path: Destination file path; written in UTF-8 text mode.

    Raises:
        ValueError: If *responses* is an empty sequence.
        OSError: If the file cannot be written.

    Note:
        Records are separated by a single blank line. Poles, zeros, and
        `CONSTANT` are written at 6 decimal digits (`.6e`), matching the
        EarthScope SACPZ web service's own output convention — a real SAC
        PZ file never carries more precision than this, so writing a
        [`SacPZ`][pysmo.classes.SacPZ] instance (which was itself parsed
        from `.6e`-formatted text) back out loses nothing. Writing a
        higher-precision source instead — e.g. a
        [`StationXML`][pysmo.classes.StationXML] instance, whose XML
        `<Real>`/`<Imaginary>` elements are not limited to 6 decimals —
        does round to this format's conventional precision; that is
        expected when converting into SAC PZ, not a bug to work around
        here. The `* SENSITIVITY` header line is omitted when
        `reference_sensitivity` is `None`. `network`/`station`/`location`/
        `channel`/`input_units` are written verbatim, with no escaping: a
        value containing a newline would produce a file this module's own
        `parse_sacpz` cannot read back correctly (a colon is fine, since
        `_HEADER_PATTERN`'s value group captures the rest of the line).
        Not a concern for real FDSN network/station/location/channel codes
        or SEED unit strings, which never contain a newline.

    Examples:
        ```python
        >>> from pathlib import Path
        >>> from pysmo.classes import SacPZ
        >>> from pysmo.lib.io import write_sacpz
        >>> text = Path("SACPZ.IU.ANMO.00.BHZ").read_text()
        >>> response = SacPZ.from_text(text)
        >>> write_sacpz(response, "out.pz")
        >>> write_sacpz([response, response], "multi.pz")
        >>>
        ```
    """
    items = responses if isinstance(responses, Sequence) else [responses]
    if not items:
        raise ValueError("responses must not be an empty sequence.")

    blocks = [_sacpz_block(response) for response in items]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks))
        f.write("\n")
