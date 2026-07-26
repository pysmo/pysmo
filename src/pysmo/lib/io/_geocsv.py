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
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np
import pandas as pd

from pysmo import MiniSeismogram
from pysmo.functions._seismogram import merge
from pysmo.typing import NonNegativeNumber

__all__ = [
    "GeoCsvDataset",
    "parse_geocsv",
    "extract_geocsv_timeseries",
    "merge_geocsv_timeseries",
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
