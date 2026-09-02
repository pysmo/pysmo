"""Low-level writing of the miniSEED waveform format.

miniSEED reading is handled directly by
[`MSeed`][pysmo.classes.MSeed] via EarthScope's `pymseed` — there is no
parsing counterpart here. `write_mseed` is the write side, kept in
`pysmo.lib.io` alongside [`write_geocsv`][pysmo.lib.io.write_geocsv] so
callers learn one import location for pysmo's format writers.
"""

from collections.abc import Sequence
from os import PathLike
from typing import Any, Literal
from warnings import warn

import numpy as np
import numpy.typing as npt
import pymseed
from pymseed import DataEncoding, MS3TraceList

from pysmo import Seismogram, StationCode

__all__ = ["write_mseed"]

_DTYPE_TO_SAMPLE_TYPE: dict[type, Literal["i", "f", "d"]] = {
    np.dtype(np.int32).type: "i",
    np.dtype(np.float32).type: "f",
    np.dtype(np.float64).type: "d",
}

_SAMPLE_TYPE_TO_ENCODING: dict[str, DataEncoding] = {
    "i": DataEncoding.STEIM2,
    "f": DataEncoding.FLOAT32,
    "d": DataEncoding.FLOAT64,
}


def _sample_type_for(data: npt.NDArray[Any]) -> Literal["i", "f", "d"]:
    """Map a data array's dtype to a miniSEED sample-type code."""
    try:
        return _DTYPE_TO_SAMPLE_TYPE[data.dtype.type]
    except KeyError:
        raise TypeError(
            f"Cannot write miniSEED from data of dtype {data.dtype}. "
            + "Supported dtypes are int32, float32 and float64; convert the "
            + "data first, or pass an explicit sample_type to accept the "
            + "conversion."
        ) from None


def write_mseed(
    segments: Sequence[tuple[StationCode, Seismogram]],
    path: str | PathLike[str],
    *,
    sample_type: Literal["i", "f", "d"] | None = None,
) -> None:
    """Write one or more waveform segments to a miniSEED file.

    Each `(identity, seismogram)` pair becomes one trace segment. Pairs
    that resolve to the same FDSN Source Identifier are grouped into one
    trace with several segments — the natural representation of a channel
    with a data gap.

    Every segment is written with publication (quality) version 1,
    regardless of any version an `MSeed` identity carries. Because
    [`MSeed`][pysmo.classes.MSeed] always decodes samples to `float64`, a
    file read with `MSeed` and written back defaults to the uncompressed
    `"d"` encoding even if the source used STEIM integer compression; pass
    `sample_type="i"` to compress integer-valued data.

    Args:
        segments: A non-empty sequence of `(identity, seismogram)` pairs.
            *identity* is any [`StationCode`][pysmo.StationCode] (e.g. a
            [`MiniStationCode`][pysmo.MiniStationCode], an
            [`MSeed`][pysmo.classes.MSeed], or a full
            [`Station`][pysmo.Station] — extra coordinate fields are
            ignored); it supplies the network, station, location and
            channel codes. *seismogram* is any
            [`Seismogram`][pysmo.Seismogram].
        path: Destination file path. Any existing content is overwritten.
        sample_type: miniSEED sample encoding: `"i"` (32-bit integer,
            STEIM2), `"f"` (32-bit float) or `"d"` (64-bit float). The
            default `None` picks it from each seismogram's `data.dtype`
            (`int32` → `"i"`, `float32` → `"f"`, `float64` → `"d"`; any
            other dtype raises `TypeError`). An explicit value is applied
            to every segment as given — a `UserWarning` is emitted per
            segment whose data does not already match, since `pymseed`
            silently truncates or downcasts in that case.

    Raises:
        TypeError: If *sample_type* is `None` and a seismogram's data has a
            dtype other than `int32`, `float32` or `float64`.
        ValueError: If *segments* is empty.
        pymseed.MiniSEEDError: If the data cannot be encoded or written.

    Examples:
        ```python
        >>> import numpy as np
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram, MiniStationCode
        >>> from pysmo.lib.io import write_mseed
        >>> identity = MiniStationCode(
        ...     name="ANMO", network="IU", location="00", channel="BHZ"
        ... )
        >>> seismogram = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        ...     delta=pd.Timedelta(seconds=0.05),
        ...     data=np.arange(100.0),
        ... )
        >>> write_mseed([(identity, seismogram)], "out.mseed")
        >>>
        ```
    """
    if not segments:
        raise ValueError("segments must not be an empty sequence.")

    tracelist = MS3TraceList()
    encodings: set[DataEncoding] = set()

    for identity, seismogram in segments:
        # pymseed reads a raw C buffer; materialise any non-contiguous view.
        data = np.ascontiguousarray(seismogram.data)
        resolved_type = sample_type or _sample_type_for(data)
        if (
            sample_type is not None
            and _DTYPE_TO_SAMPLE_TYPE.get(data.dtype.type) != sample_type
        ):
            warn(
                f"Writing {data.dtype} data as sample_type {sample_type!r}; "
                + "pymseed will convert each sample, which may lose precision.",
                UserWarning,
                stacklevel=2,
            )
        encodings.add(_SAMPLE_TYPE_TO_ENCODING[resolved_type])
        sourceid = pymseed.nslc2sourceid(
            identity.network,
            identity.name,
            identity.location,
            identity.channel,
        )
        tracelist.add_data(
            sourceid=sourceid,
            data_samples=data,
            sample_type=resolved_type,
            sample_rate=1_000_000_000 / seismogram.delta.value,
            starttime=seismogram.begin_time.value,
            publication_version=1,
        )

    if len(encodings) > 1:
        raise ValueError(
            "All segments in one miniSEED file must share a sample encoding; "
            + "pass a single explicit sample_type, or write segments of "
            + "differing dtype to separate files."
        )

    tracelist.to_file(path, overwrite=True, encoding=encodings.pop())
