"""Low-level parsing of the GeoCSV tabular text format.

This module implements the parsing side of the [GeoCSV 2.0
specification](https://ds.iris.edu/files/documents/GeoCSV.pdf). GeoCSV is a
generic container: a single text body may hold several self-contained
datasets of arbitrary content (timeseries, station tables, event
catalogues, ...), each introduced by a `dataset:` keyword line.

[`parse_geocsv`][pysmo.lib.io.parse_geocsv] splits a text body into
raw [`GeoCsvDataset`][pysmo.lib.io.GeoCsvDataset] instances without
interpreting them. [`extract_geocsv_timeseries`][pysmo.lib.io.extract_geocsv_timeseries]
and [`merge_geocsv_timeseries`][pysmo.lib.io.merge_geocsv_timeseries] interpret
datasets as waveform segments using the extension keywords emitted by the
EarthScope FDSN dataselect service (`SID`, `start_time`, `sample_rate_hz`,
`sample_count`).
"""

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property
from os import PathLike

import numpy as np
import pandas as pd

from pysmo import MiniSeismogram, Seismogram
from pysmo.functions._seismogram import merge
from pysmo.typing import NonNegativeNumber

__all__ = [
    "GeoCsvDataset",
    "parse_geocsv",
    "extract_geocsv_timeseries",
    "merge_geocsv_timeseries",
    "write_geocsv",
]

_KEYWORD_PATTERN = re.compile(r"^\s*#\s*([^:]+?)\s*:\s*(.*?)\s*$")
"""Keyword comment line as defined in the GeoCSV specification."""

_DELIMITER_ESCAPES = {r"\s": " ", r"\t": "\t", r"\\": "\\"}
"""Backslash escape sequences allowed as `delimiter` keyword values."""

_SAMPLE_FIELD_TYPES = ("integer", "float")
"""GeoCSV `field_type` values that denote a numeric sample column."""


@dataclass
class GeoCsvDataset:
    """A single uninterpreted dataset from a GeoCSV text body."""

    headers: dict[str, str] = field(default_factory=dict)
    """Keyword comment values, keyed by lowercased keyword."""

    column_names: list[str] = field(default_factory=list)
    """Field names from the header line."""

    rows: list[list[str]] = field(default_factory=list)
    """Data lines split on the dataset delimiter, values stripped of
    surrounding whitespace."""

    @cached_property
    def delimiter(self) -> str:
        """Field delimiter for this dataset (defaults to a comma)."""
        delimiter = self.headers.get("delimiter", ",")
        delimiter = _DELIMITER_ESCAPES.get(delimiter, delimiter)
        if len(delimiter) != 1:
            raise ValueError(
                f"GeoCSV delimiter must be a single character, got {delimiter!r}."
            )
        return delimiter


@dataclass
class _TimeseriesSegment:
    """A GeoCSV dataset interpreted as a contiguous waveform segment."""

    start_time: pd.Timestamp
    sample_rate_hz: float
    sample_count: int
    sid: str
    data: np.ndarray


def _parse_fields(line: str, delimiter: str) -> list[str]:
    """Parse a GeoCSV line using CSV semantics for the given delimiter."""
    reader = csv.reader([line], delimiter=delimiter, skipinitialspace=True)
    return [value.strip() for value in next(reader)]


def parse_geocsv(text: str) -> list[GeoCsvDataset]:
    """Split a GeoCSV text body into a list of datasets.

    A new dataset starts at every `dataset:` keyword line. Keyword lines
    are recognised with the whitespace flexibility the specification
    allows (e.g. `#dataset:GeoCSV 2.0` is equivalent to
    `# dataset: GeoCSV 2.0`). Comment lines without a keyword are
    ignored. The first non-comment line of each dataset is taken as the
    column header line; all further non-comment lines are data rows,
    split on the dataset delimiter.

    Args:
        text: GeoCSV text body.

    Returns:
        List of uninterpreted datasets in order of appearance.
    """
    datasets: list[GeoCsvDataset] = []
    current: GeoCsvDataset | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if match := _KEYWORD_PATTERN.match(line):
            keyword, value = match.group(1).lower(), match.group(2)
            if keyword == "dataset" or current is None:
                current = GeoCsvDataset()
                datasets.append(current)
            current.headers[keyword] = value
            continue
        if stripped.startswith("#"):
            continue
        if current is None:
            current = GeoCsvDataset()
            datasets.append(current)
        values = _parse_fields(line, current.delimiter)
        if current.column_names:
            current.rows.append(values)
        else:
            current.column_names = values

    return datasets


def _find_sample_column(dataset: GeoCsvDataset) -> int:
    """Locate the numeric sample column via `field_type`."""
    field_types = dataset.headers.get("field_type", "")
    for index, field_type in enumerate(_parse_fields(field_types, dataset.delimiter)):
        if field_type.lower() in _SAMPLE_FIELD_TYPES:
            return index
    raise ValueError(
        "Cannot determine sample column: no 'field_type' header with a numeric "
        f"type ({', '.join(_SAMPLE_FIELD_TYPES)}) found in GeoCSV dataset."
    )


def extract_geocsv_timeseries(dataset: GeoCsvDataset) -> _TimeseriesSegment:
    """Interpret a GeoCSV dataset as a waveform segment.

    Uses the timeseries extension keywords emitted by the EarthScope FDSN
    dataselect service (`SID`, `start_time`, `sample_rate_hz`,
    `sample_count`). The sample column is located via the `field_type`
    keyword; the dataset must declare a numeric `field_type`.

    Args:
        dataset: Uninterpreted GeoCSV dataset.

    Returns:
        The dataset as a waveform segment.

    Raises:
        ValueError: If a required timeseries header is missing, no numeric
            `field_type` column is found, or the number of data rows does
            not match the declared `sample_count` (e.g. a truncated
            response).
    """
    headers = dataset.headers
    try:
        _ts = pd.Timestamp(headers["start_time"])
        start_time = _ts if _ts.tzinfo is not None else _ts.tz_localize("UTC")
        sample_rate_hz = float(headers["sample_rate_hz"])
        sample_count = int(headers["sample_count"])
    except KeyError as error:
        raise ValueError(
            f"GeoCSV dataset is missing required timeseries header {error}."
        ) from error

    if dataset.rows:
        sample_column = _find_sample_column(dataset)
        try:
            data = np.array(
                [row[sample_column] for row in dataset.rows], dtype=np.float64
            )
        except IndexError as error:
            raise ValueError(
                f"GeoCSV dataset row has fewer than {sample_column + 1} fields; "
                "cannot locate the sample column declared by 'field_type'."
            ) from error
    else:
        data = np.array([], dtype=np.float64)

    if len(data) != sample_count:
        raise ValueError(
            f"GeoCSV dataset declares sample_count {sample_count} "
            f"but contains {len(data)} data rows."
        )

    return _TimeseriesSegment(
        start_time=start_time,
        sample_rate_hz=sample_rate_hz,
        sample_count=sample_count,
        sid=headers.get("sid", ""),
        data=data,
    )


def merge_geocsv_timeseries(
    segments: list[_TimeseriesSegment],
    *,
    gap_tolerance_factor: NonNegativeNumber = 0.5,
    auto_delta: bool = False,
) -> _TimeseriesSegment:
    """Merge contiguous waveform segments into a single segment.

    Zero-sample segments are discarded before merging; the remaining
    segments must share a channel (SID) and sample rate. The merge itself —
    chronological ordering, gap/overlap tolerance, and overlap verification —
    is delegated to
    [`merge`][pysmo.functions.merge]; see its
    docstring for details.

    Args:
        segments: Waveform segments to merge, in any order.
        gap_tolerance_factor: Maximum allowed boundary timestamp jitter
            between consecutive segments, as a fraction of the sampling
            interval. Passed through to
            [`merge`][pysmo.functions.merge].
        auto_delta: Estimate a common sampling interval with
            [`estimate_delta`][pysmo.functions.estimate_delta] instead of
            requiring segments to share the exact same sample rate — useful
            when reported sample rates only disagree by measurement or
            floating-point noise. Passed through to
            [`merge`][pysmo.functions.merge].

    Returns:
        A single segment covering all input segments.

    Raises:
        ValueError: If no non-empty segments remain, the segments belong
            to different channels, the sample rates differ and `auto_delta`
            is `False`, or the underlying merge fails (see
            [`merge`][pysmo.functions.merge]).
    """
    if gap_tolerance_factor < 0:
        raise ValueError("gap_tolerance_factor must be non-negative.")

    segments = [segment for segment in segments if segment.sample_count > 0]
    if not segments:
        raise ValueError("No non-empty timeseries segments to merge.")

    sids = {segment.sid for segment in segments}
    if len(sids) > 1:
        raise ValueError(
            f"Cannot merge segments from different channels: {sorted(sids)}."
        )

    if len(segments) == 1:
        return segments[0]

    if not auto_delta:
        sample_rates = {segment.sample_rate_hz for segment in segments}
        if len(sample_rates) > 1:
            raise ValueError(
                f"Cannot merge segments with different sample rates: "
                f"{sorted(sample_rates)} Hz."
            )

    reference = segments[0]
    mini_seismograms = tuple(
        MiniSeismogram(
            begin_time=segment.start_time,
            delta=pd.Timedelta(seconds=1.0 / segment.sample_rate_hz),
            data=segment.data,
        )
        for segment in segments
    )
    # merge's `delta`/`auto_delta` overloads require a literal
    # `auto_delta`, which a plain `bool` variable can't satisfy; branching
    # here lets each call site narrow to the right overload.
    if auto_delta:
        merged = merge(
            mini_seismograms,
            auto_delta=True,
            gap_tolerance_factor=gap_tolerance_factor,
            clone=True,
        )
    else:
        merged = merge(
            mini_seismograms,
            gap_tolerance_factor=gap_tolerance_factor,
            clone=True,
        )
    return _TimeseriesSegment(
        start_time=merged.begin_time,
        # `.value` (integer nanoseconds) rather than `.total_seconds()`:
        # the latter loses sub-microsecond precision, which matters here
        # since `merged.delta` may be an auto_delta-estimated value only
        # a few nanoseconds off from a round number.
        sample_rate_hz=1_000_000_000 / merged.delta.value,
        sample_count=len(merged.data),
        sid=reference.sid,
        data=merged.data,
    )


def _geocsv_block(seismogram: Seismogram) -> str:
    """Render a single Seismogram as one GeoCSV 2.0 dataset block."""
    sid = getattr(seismogram, "sid", None)
    data = seismogram.data
    sample_count = len(data)
    # `.value` (integer nanoseconds) rather than `.total_seconds()`: the
    # latter loses sub-microsecond precision and can even round a valid
    # delta down to zero, raising ZeroDivisionError.
    sample_rate_hz = 1_000_000_000 / seismogram.delta.value

    # np.isfinite(...) guards against `int(inf)` raising OverflowError below —
    # inf/-inf trivially satisfy `x == round(x)` but are not representable as
    # int; route them (and NaN) through the float branch instead.
    is_integral = bool(np.all(np.isfinite(data)) and np.all(data == np.round(data)))
    field_type = "integer" if is_integral else "float"

    lines = [
        "# dataset: GeoCSV 2.0",
        "# delimiter: ,",
        "# field_unit: UTC, Counts",
        f"# field_type: datetime, {field_type}",
    ]
    if sid is not None:
        lines.append(f"# SID: {sid}")
    lines.extend(
        [
            f"# sample_count: {sample_count}",
            f"# sample_rate_hz: {sample_rate_hz}",
            f"# start_time: {seismogram.begin_time.isoformat()}",
            "Time, Sample",
        ]
    )

    for n, sample in enumerate(data):
        timestamp = (seismogram.begin_time + n * seismogram.delta).isoformat()
        formatted_sample = str(int(sample)) if is_integral else repr(float(sample))
        lines.append(f"{timestamp}, {formatted_sample}")

    return "\n".join(lines)


def write_geocsv(
    seismograms: Seismogram | Sequence[Seismogram],
    path: str | PathLike,
) -> None:
    """Write one or more Seismogram objects to a GeoCSV 2.0 file.

    Each object is serialised as a self-contained GeoCSV 2.0 timeseries
    dataset block (`# dataset: GeoCSV 2.0` header, keyword metadata,
    column header line, one row per sample). Multiple objects produce a
    multi-dataset file that is readable by
    [`parse_geocsv`][pysmo.lib.io.parse_geocsv].

    Args:
        seismograms: A single [`Seismogram`][pysmo.Seismogram] or a
            non-empty sequence of them.
        path: Destination file path. Written in UTF-8 text mode;
            existing content is overwritten.

    Raises:
        ValueError: If *seismograms* is an empty sequence.
        OSError: If the file cannot be written.

    Note:
        Dataset blocks are separated by a single blank line. The
        `sample_rate_hz` header value is derived from
        `1_000_000_000 / delta.value` (integer nanoseconds, to preserve
        sub-microsecond precision). Both the `# start_time:` header and
        every `Time` column value are `pd.Timestamp.isoformat()` calls
        (`begin_time` and `begin_time + n * delta` respectively), which
        preserve full precision (including nanoseconds). Sample values are
        written as `integer` or `float` depending on whether the data is
        integral, so genuinely non-integral data (e.g. a detrended or
        filtered seismogram) is never silently truncated. A `sid` attribute
        is used if present (e.g. on a
        [`GeoCsvSeismogram`][pysmo.classes.GeoCsvSeismogram]), but is not
        required by the [`Seismogram`][pysmo.Seismogram] protocol itself,
        so the `# SID:` header line is simply omitted for objects that
        don't have one. `# field_unit: UTC, Counts` is always written as-is
        — neither `Seismogram` nor `GeoCsvSeismogram` carries a units
        concept, so this label may not describe the data's actual physical
        units (e.g. after response removal); `parse_geocsv`/
        `extract_geocsv_timeseries` never read it back, so this doesn't
        affect round-tripping, only external readers. `sid` is written
        verbatim, with no escaping: a value containing a newline would
        produce a file this module's own `parse_geocsv` cannot read back
        correctly (a comma is fine, since header lines are matched by
        regex, not CSV-split). Not a concern for real FDSN source
        identifiers, which never contain a newline.

    Examples:
        ```python
        >>> import pandas as pd
        >>> import numpy as np
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.lib.io import write_geocsv
        >>> now = pd.Timestamp.now("UTC")
        >>> delta = pd.Timedelta(seconds=0.1)
        >>> seg1 = MiniSeismogram(begin_time=now, delta=delta, data=np.arange(5.0))
        >>> seg2 = MiniSeismogram(begin_time=now, delta=delta, data=np.arange(5.0))
        >>> write_geocsv(seg1, "out.geocsv")
        >>> write_geocsv([seg1, seg2], "multi.geocsv")
        >>>
        ```
    """
    items = seismograms if isinstance(seismograms, Sequence) else [seismograms]
    if not items:
        raise ValueError("seismograms must not be an empty sequence.")

    blocks = [_geocsv_block(seismogram) for seismogram in items]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks))
        f.write("\n")
