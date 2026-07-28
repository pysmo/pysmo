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
from dataclasses import dataclass

import pandas as pd

from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = ["parse_sacpz"]

_HEADER_PATTERN = re.compile(
    r"^\*\s*([A-Za-z][A-Za-z ]*?)\s*(?:\([^)]*\))?\s*:\s*(.*?)\s*$"
)
"""A `* KEY (SACHDR): value` or `* KEY: value` comment header line."""

_REQUIRED_HEADERS = ("NETWORK", "STATION", "LOCATION", "CHANNEL", "START", "INPUT UNIT")


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
        real, imag = (float(part) for part in lines[index].split())
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
        overall_sensitivity = float(constant_line.split()[1])
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
                    float(sensitivity_text.split()[0]) if sensitivity_text else None
                ),
                input_units=headers["INPUT UNIT"],
            )
        )

    return records
