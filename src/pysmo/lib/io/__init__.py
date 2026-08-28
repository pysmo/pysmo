"""Low-level I/O classes for reading and writing seismological data.

Classes in this module handle file format details but do not implement
[`pysmo`][] protocol types directly. The `parse_*` functions here return
uninterpreted raw records meant to be wrapped by a [`pysmo.classes`][] type
before use, and should generally not be used directly for that reason.
[`write_geocsv`][pysmo.lib.io.write_geocsv] is the exception: it accepts any
object satisfying the relevant `pysmo` protocol directly (not just a
`pysmo.classes` type) and is intended to be used directly, either standalone
or via [`GeoCsvSeismogram.write`][pysmo.classes.GeoCsvSeismogram.write].
"""

from ..._utils import export_module_names
from ._geocsv import (
    GeoCsvDataset,
    extract_geocsv_timeseries,
    merge_geocsv_timeseries,
    parse_geocsv,
    write_geocsv,
)
from ._http import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    http_get,
)
from ._quakeml import parse_quakeml
from ._sacio import SacIO
from ._sacpz import parse_sacpz
from ._stationxml import parse_stationxml

__all__ = [
    "DEFAULT_REQUEST_RETRIES",
    "DEFAULT_RETRY_DELAY_SECONDS",
    "DEFAULT_TIMEOUT_SECONDS",
    "GeoCsvDataset",
    "SacIO",
    "extract_geocsv_timeseries",
    "http_get",
    "merge_geocsv_timeseries",
    "parse_geocsv",
    "parse_quakeml",
    "parse_sacpz",
    "parse_stationxml",
    "write_geocsv",
]

export_module_names(globals(), __name__)
