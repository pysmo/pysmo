"""miniSEED import/export class compatible with pysmo types."""

from os import PathLike
from typing import Self

import numpy as np
import pandas as pd
import pymseed
from attrs import cmp_using, define, field, setters, validators
from pymseed.mstracelist import MS3TraceList, MS3TraceSeg

from pysmo import MiniStationCode, Station
from pysmo._types.seismogram import SeismogramEndtimeMixin
from pysmo.lib.io import write_mseed
from pysmo.lib.validators import convert_to_timedelta, convert_to_utc_timestamp
from pysmo.tools.web import fetch_mseed
from pysmo.typing import PositiveTimedelta, UtcTimestamp

__all__ = ["MSeed"]


def _convert_mseed_data(value: object) -> np.ndarray:
    """Coerce decoded samples to a `float64` array, always via a copy.

    `pymseed` yields whatever libmseed decoded — usually `int32` for
    STEIM-compressed data — as a zero-copy view into memory owned by the
    trace list. The copy both matches pysmo's floating-point `data`
    convention and detaches the array from that memory, which is freed when
    the trace list is closed.
    """
    return np.array(value, dtype=np.float64)


def _segments(tracelist: MS3TraceList) -> list[tuple[str, int, MS3TraceSeg]]:
    """Flatten a trace list into `(sourceid, publication_version, segment)` tuples."""
    return [
        (trace_id.sourceid, trace_id.pubversion, segment)
        for trace_id in tracelist
        for segment in trace_id
    ]


@define(kw_only=True)
class MSeed(SeismogramEndtimeMixin):
    """Import/export class for one contiguous miniSEED trace segment.

    Wraps EarthScope's `pymseed` and exposes a single regularly-sampled
    segment as a [`Seismogram`][pysmo.Seismogram]-compatible object. The
    `pymseed` trace-list hierarchy is flattened at read time: each
    contiguous segment becomes one `MSeed`.

    miniSEED carries no station coordinates and no event data — only
    channel identity, timing and samples. `MSeed` exposes the network,
    station, location and channel codes as read-only properties derived
    from `sourceid` (an `MSeed` is a [`StationCode`][pysmo.StationCode] at
    runtime), but not [`Station`][pysmo.Station]. `sourceid` is the single
    authoritative identity value; to relabel, set it directly. For a
    `Station`, build a [`MiniStation`][pysmo.MiniStation] (or fetch a
    [`StationXML`][pysmo.classes.StationXML]) separately and combine.

    Use [`from_file`][pysmo.classes.MSeed.from_file] /
    [`from_bytes`][pysmo.classes.MSeed.from_bytes] to read a single
    segment, their `all_*` counterparts to read every segment, and
    [`fetch`][pysmo.classes.MSeed.fetch] to read directly from the
    EarthScope dataselect web service. Use
    [`write`][pysmo.classes.MSeed.write] to serialise back to a miniSEED
    file, or [`pysmo.lib.io.write_mseed`][] to write several segments in a
    single call.

    Examples:
        ```python
        >>> from pysmo import Seismogram, Station, StationCode
        >>> from pysmo.classes import MSeed
        >>> seismogram = MSeed.from_file("example.mseed")
        >>> isinstance(seismogram, Seismogram)
        True
        >>> isinstance(seismogram, StationCode)
        True
        >>> isinstance(seismogram, Station)
        False
        >>> seismogram.sourceid
        'FDSN:IU_ANMO_00_B_H_Z'
        >>> seismogram.network, seismogram.name, seismogram.location, seismogram.channel
        ('IU', 'ANMO', '00', 'BHZ')
        >>>
        ```
    """

    begin_time: UtcTimestamp = field(
        converter=convert_to_utc_timestamp,
        on_setattr=setters.convert,
    )
    """Seismogram begin time."""

    delta: PositiveTimedelta = field(
        converter=convert_to_timedelta,
        validator=[
            validators.instance_of(pd.Timedelta),
            validators.gt(pd.Timedelta(0)),
        ],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Seismogram sampling interval."""

    data: np.ndarray = field(
        converter=_convert_mseed_data,
        validator=validators.instance_of(np.ndarray),
        on_setattr=setters.pipe(setters.convert, setters.validate),
        eq=cmp_using(eq=np.array_equal),
    )
    """Seismogram data, always `float64`."""

    sourceid: str = field(
        validator=validators.instance_of(str),
        on_setattr=setters.validate,
    )
    """FDSN Source Identifier this segment was read from.

    The full URN form as carried in miniSEED and returned by `pymseed`,
    e.g. `FDSN:IU_ANMO_00_B_H_Z` — the `FDSN:` prefix is kept and the
    channel is split into band/source/subsource. This differs from
    [`GeoCsvSeismogram.sourceid`][pysmo.classes.GeoCsvSeismogram.sourceid],
    which keeps the shorter GeoCSV `SID` header form. This is parse-time
    metadata and is not updated when other attributes change.
    """

    publication_version: int = field(converter=int)
    """miniSEED publication (quality) version this segment was read from."""

    @property
    def network(self) -> str:
        """Network code, derived from `sourceid` (read-only)."""
        return pymseed.sourceid2nslc(self.sourceid)[0]

    @property
    def name(self) -> str:
        """Station code, derived from `sourceid` (read-only)."""
        return pymseed.sourceid2nslc(self.sourceid)[1]

    @property
    def location(self) -> str:
        """Location code, derived from `sourceid` (read-only)."""
        return pymseed.sourceid2nslc(self.sourceid)[2]

    @property
    def channel(self) -> str:
        """Channel code, derived from `sourceid` (read-only)."""
        return pymseed.sourceid2nslc(self.sourceid)[3]

    @property
    def sample_count(self) -> int:
        """Number of samples, always equal to `len(data)`."""
        return len(self.data)

    @classmethod
    def _from_segment(
        cls, sourceid: str, publication_version: int, segment: MS3TraceSeg
    ) -> Self:
        return cls(
            begin_time=pd.Timestamp(segment.starttime, unit="ns", tz="UTC"),
            delta=pd.Timedelta(seconds=1.0 / segment.samprate),
            data=segment.np_datasamples,
            sourceid=sourceid,
            publication_version=publication_version,
        )

    @classmethod
    def _all_from_tracelist(cls, tracelist: MS3TraceList) -> list[Self]:
        return [cls._from_segment(*entry) for entry in _segments(tracelist)]

    @classmethod
    def _one_from_tracelist(cls, tracelist: MS3TraceList, source: str) -> Self:
        segments = cls._all_from_tracelist(tracelist)
        if len(segments) == 1:
            return segments[0]
        if not segments:
            raise ValueError(f"No miniSEED data found in {source}.")
        segment_lines = "\n".join(
            f"  {s.network}.{s.name}.{s.location}.{s.channel}  "
            f"{s.begin_time} -- {s.end_time}"
            for s in segments
        )
        raise ValueError(
            f"{source} holds {len(segments)} contiguous segments; "
            f"MSeed.from_bytes()/from_file() requires exactly one. Use "
            f"MSeed.all_from_bytes()/all_from_file() instead. Segments found:\n"
            f"{segment_lines}"
        )

    @classmethod
    def from_file(cls, filename: str | PathLike[str]) -> Self:
        """Create a new instance from a miniSEED file holding exactly one contiguous segment.

        Args:
            filename: Path to the miniSEED file to read.

        Returns:
            A new MSeed instance.

        Raises:
            ValueError: If the file holds zero, or more than one, contiguous
                segment (a data gap, or more than one channel).
            pymseed.MiniSEEDError: If the file cannot be read as miniSEED.
        """
        with MS3TraceList.from_file(filename, unpack_data=True) as tracelist:
            return cls._one_from_tracelist(tracelist, f"file {filename!r}")

    @classmethod
    def all_from_file(cls, filename: str | PathLike[str]) -> list[Self]:
        """Create one instance per contiguous segment in a miniSEED file.

        Args:
            filename: Path to the miniSEED file to read.

        Returns:
            One MSeed instance per contiguous segment, grouped by source
            identifier and ordered by time within each. Empty if the file
            holds no data.

        Raises:
            pymseed.MiniSEEDError: If the file cannot be read as miniSEED.
        """
        with MS3TraceList.from_file(filename, unpack_data=True) as tracelist:
            return cls._all_from_tracelist(tracelist)

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Create a new instance from miniSEED bytes holding exactly one contiguous segment.

        Args:
            data: Raw miniSEED bytes.

        Returns:
            A new MSeed instance.

        Raises:
            ValueError: If the data holds zero, or more than one, contiguous
                segment (a data gap, or more than one channel).
            pymseed.MiniSEEDError: If the data cannot be read as miniSEED.
        """
        with MS3TraceList.from_buffer(data, unpack_data=True) as tracelist:
            return cls._one_from_tracelist(tracelist, "the given bytes")

    @classmethod
    def all_from_bytes(cls, data: bytes) -> list[Self]:
        """Create one instance per contiguous segment in miniSEED bytes.

        Args:
            data: Raw miniSEED bytes.

        Returns:
            One MSeed instance per contiguous segment, grouped by source
            identifier and ordered by time within each. Empty if the data
            holds no segments.

        Raises:
            pymseed.MiniSEEDError: If the data cannot be read as miniSEED.
        """
        with MS3TraceList.from_buffer(data, unpack_data=True) as tracelist:
            return cls._all_from_tracelist(tracelist)

    @classmethod
    def fetch(
        cls, *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> Self:
        """Fetch and parse a seismogram from the EarthScope FDSN dataselect web service, for an absolute time window.

        For a window relative to a predicted phase arrival instead, compute
        the window yourself (e.g. with [`pysmo.tools.web.fetch_travel_times`][],
        which shows exactly this in its own Examples) and pass the
        resulting *starttime*/*endtime* here.

        To fetch once and interpret later (e.g. offline, or without
        repeating the network request), use
        [`pysmo.tools.web.fetch_mseed`][] and
        [`from_bytes`][pysmo.classes.MSeed.from_bytes] /
        [`all_from_bytes`][pysmo.classes.MSeed.all_from_bytes] directly
        instead.

        Args:
            station: Any object satisfying the [`Station`][pysmo.Station]
                protocol. Provides the network, station code, location, and
                channel for the request.
            starttime: Start of the requested time window (UTC).
            endtime: End of the requested time window (UTC).

        Returns:
            A new MSeed instance.

        Raises:
            ValueError: If no waveform data is returned for the given
                window, or more than one contiguous segment is returned
                (a data gap, or a wildcarded channel/location code matching
                more than one channel).
            urllib3.exceptions.ResponseError: If the dataselect web service
                returns an HTTP error.

        Examples:
            <!-- skip: start if(not run_real_web_requests) -->
            ```python
            >>> import pandas as pd
            >>> from pysmo import MiniStation
            >>> from pysmo.classes import MSeed
            >>> station = MiniStation(
            ...     name="ANMO", network="IU", location="00", channel="LHZ",
            ...     latitude=34.945981, longitude=-106.457133,
            ... )
            >>> seismogram = MSeed.fetch(
            ...     station=station,
            ...     starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
            ...     endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
            ... )
            >>>
            ```
            <!-- skip: end -->
        """
        starttime = convert_to_utc_timestamp(starttime)
        endtime = convert_to_utc_timestamp(endtime)
        waveform_bytes = fetch_mseed(
            station=station, starttime=starttime, endtime=endtime
        )
        if not waveform_bytes:
            raise ValueError(
                f"No waveform data returned for "
                f"{station.network}.{station.name}.{station.location}."
                f"{station.channel} between {starttime} and {endtime}."
            )
        return cls.from_bytes(waveform_bytes)

    def write(self, path: str | PathLike[str]) -> None:
        """Write this seismogram to a miniSEED file.

        Samples are written as `float64` (uncompressed) and the
        publication version is set to 1 — `sourceid` and timing are
        preserved, `publication_version` is not. For STEIM integer
        compression, or to write several seismograms into one file, use
        [`pysmo.lib.io.write_mseed`][] directly.

        Args:
            path: Destination file path. Any existing content is
                overwritten.
        """
        identity = MiniStationCode(
            network=self.network,
            name=self.name,
            location=self.location,
            channel=self.channel,
        )
        write_mseed([(identity, self)], path)
