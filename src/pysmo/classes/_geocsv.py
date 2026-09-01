"""GeoCSV import classes compatible with pysmo types."""

from os import PathLike
from typing import Self

import numpy as np
import numpy.typing as npt
import pandas as pd
from attrs import cmp_using, define, field, setters, validators

from pysmo import Station
from pysmo._types.seismogram import SeismogramEndtimeMixin
from pysmo.lib.io import (
    extract_geocsv_timeseries,
    merge_geocsv_timeseries,
    parse_geocsv,
    write_geocsv,
)
from pysmo.lib.validators import (
    convert_to_ndarray,
    convert_to_timedelta,
    convert_to_utc_timestamp,
)
from pysmo.tools.web import fetch_geocsvseismogram
from pysmo.typing import PositiveTimedelta, UtcTimestamp

__all__ = ["GeoCsvSeismogram"]


@define(kw_only=True)
class GeoCsvSeismogram(SeismogramEndtimeMixin):
    r"""Import/export class for seismograms in the GeoCSV timeseries format.

    Reads a waveform from the timeseries flavour of
    [GeoCSV](https://ds.iris.edu/files/documents/GeoCSV.pdf) and exposes
    it as a [`Seismogram`][pysmo.Seismogram]-compatible object.

    This class is intended as a data-ingestion step. Once loaded, use
    [`clone_to_mini`][pysmo.functions.clone_to_mini] to convert the
    waveform to a [`MiniSeismogram`][pysmo.MiniSeismogram], which can then
    be passed to [`copy_from_mini`][pysmo.functions.copy_from_mini] to
    populate another object such as a [`SAC`][pysmo.classes.SAC] instance.
    Use [`write`][pysmo.classes.GeoCsvSeismogram.write] to serialise the
    instance back to a GeoCSV 2.0 file, or [`pysmo.lib.io.write_geocsv`][]
    to write one or more `Seismogram`-compatible objects in a single call.

    Examples:
        ```python
        >>> from pysmo.classes import GeoCsvSeismogram
        >>> text = '''\
        ... # dataset: GeoCSV 2.0
        ... # delimiter: ,
        ... # field_unit: UTC, Counts
        ... # field_type: datetime, INTEGER
        ... # SID: IU_ANMO_00_LHZ
        ... # sample_count: 3
        ... # sample_rate_hz: 1.0
        ... # start_time: 2010-02-27T06:30:00Z
        ... Time, Sample
        ... 2010-02-27T06:30:00Z, -47297
        ... 2010-02-27T06:30:01Z, -47298
        ... 2010-02-27T06:30:02Z, -47299'''
        >>> seismogram = GeoCsvSeismogram.from_text(text)
        >>> seismogram.sourceid
        'IU_ANMO_00_LHZ'
        >>> seismogram.data
        array([-47297., -47298., -47299.])
        >>> seismogram.end_time
        Timestamp('2010-02-27 06:30:02+0000', tz='UTC')
        >>> import pathlib
        >>> seismogram.write("out.geocsv"); recovered = GeoCsvSeismogram.from_text(pathlib.Path("out.geocsv").read_text())
        >>> recovered.sourceid
        'IU_ANMO_00_LHZ'
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

    data: npt.NDArray[np.floating] = field(
        converter=convert_to_ndarray,
        validator=validators.instance_of(np.ndarray),
        on_setattr=setters.pipe(setters.convert, setters.validate),
        eq=cmp_using(eq=np.array_equal),
    )
    """Seismogram data."""

    sourceid: str = field(
        validator=validators.instance_of(str),
        on_setattr=setters.validate,
    )
    """FDSN Source Identifier as carried in the GeoCSV `SID` header.

    Stored verbatim as parsed, e.g. `IU_ANMO_00_LHZ` — no `FDSN:` URN
    prefix, and the channel is not split into band/source/subsource. This
    differs from [`MSeed.sourceid`][pysmo.classes.MSeed.sourceid], which
    keeps the full URN form. This is parse-time metadata: it describes the
    GeoCSV data the instance was created from and is not updated when other
    attributes change.
    """

    @property
    def sample_count(self) -> int:
        """Number of samples, always equal to `len(data)`."""
        return len(self.data)

    @classmethod
    def from_text(cls, text: str) -> Self:
        """Create a new instance from a GeoCSV text body.

        The text may contain several timeseries datasets (the EarthScope
        dataselect service returns one dataset per contiguous segment);
        they are merged into a single continuous waveform.

        Args:
            text: GeoCSV text containing one or more timeseries datasets.

        Returns:
            A new GeoCsvSeismogram instance.

        Raises:
            ValueError: If the text contains no GeoCSV datasets, a dataset
                is not a valid timeseries, or the datasets cannot be merged
                into a continuous waveform (data gaps, differing channels
                or sample rates).
        """
        datasets = parse_geocsv(text)
        if not datasets:
            raise ValueError("No GeoCSV datasets found in text.")
        segment = merge_geocsv_timeseries(
            [extract_geocsv_timeseries(dataset) for dataset in datasets]
        )
        return cls(
            begin_time=segment.start_time,
            delta=pd.Timedelta(seconds=1.0 / segment.sample_rate_hz),
            data=segment.data,
            sourceid=segment.sourceid,
        )

    @classmethod
    def fetch(
        cls, *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> Self:
        """Fetch and parse a seismogram from the EarthScope FDSN dataselect web service, for an absolute time window.

        For a window relative to a predicted phase arrival instead, compute
        the window yourself (e.g. with
        [`pysmo.tools.traveltime.travel_times`][], which shows exactly this
        in its own Examples) and pass the resulting *starttime*/*endtime*
        here.

        Args:
            station: Any object satisfying the [`Station`][pysmo.Station]
                protocol. Provides the network, station code, location, and
                channel for the request.
            starttime: Start of the requested time window (UTC).
            endtime: End of the requested time window (UTC).

        Returns:
            A new GeoCsvSeismogram instance.

        Raises:
            ValueError: If no waveform data is returned for the given window,
                or the returned segments cannot be merged into a continuous
                trace (data gaps, differing channels or sample rates).
            urllib3.exceptions.ResponseError: If the dataselect web service
                returns an HTTP error.

        Examples:
            <!-- skip: start if(not run_real_web_requests) -->
            ```python
            >>> import pandas as pd
            >>> from pysmo import MiniStation
            >>> from pysmo.classes import GeoCsvSeismogram
            >>> station = MiniStation(
            ...     name="ANMO", network="IU", location="00", channel="LHZ",
            ...     latitude=34.945981, longitude=-106.457133,
            ... )
            >>> seismogram = GeoCsvSeismogram.fetch(
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
        waveform_bytes = fetch_geocsvseismogram(
            station=station, starttime=starttime, endtime=endtime
        )
        if not waveform_bytes.strip():
            raise ValueError(
                "No waveform data returned for "
                + f"{station.network}.{station.name}.{station.location}."
                + f"{station.channel} between {starttime} and {endtime}."
            )
        return cls.from_text(waveform_bytes.decode("utf-8"))

    def write(self, path: str | PathLike[str]) -> None:
        r"""Write this seismogram to a GeoCSV 2.0 file.

        Serialises the instance as a single GeoCSV 2.0 timeseries dataset.
        To write several seismograms into one multi-dataset file use
        [`pysmo.lib.io.write_geocsv`][] directly.

        Args:
            path: Destination file path. The file is written in UTF-8 text
                mode and any existing content is overwritten.

        Examples:
            ```python
            >>> import pathlib
            >>> from pysmo.classes import GeoCsvSeismogram
            >>> text = '''\
            ... # dataset: GeoCSV 2.0
            ... # delimiter: ,
            ... # field_unit: UTC, Counts
            ... # field_type: datetime, INTEGER
            ... # SID: IU_ANMO_00_LHZ
            ... # sample_count: 3
            ... # sample_rate_hz: 1.0
            ... # start_time: 2010-02-27T06:30:00Z
            ... Time, Sample
            ... 2010-02-27T06:30:00Z, -47297
            ... 2010-02-27T06:30:01Z, -47298
            ... 2010-02-27T06:30:02Z, -47299'''
            >>> seismogram = GeoCsvSeismogram.from_text(text)
            >>> seismogram.write("out.geocsv"); recovered = GeoCsvSeismogram.from_text(
            ...     pathlib.Path("out.geocsv").read_text()
            ... )
            >>> recovered.sourceid == seismogram.sourceid
            True
            >>>
            ```
        """
        write_geocsv(self, path)
