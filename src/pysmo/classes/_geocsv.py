"""GeoCSV import classes compatible with pysmo types."""

from typing import Self

import numpy as np
import pandas as pd
from attrs import define, field, setters, validators

from pysmo._types.seismogram import SeismogramEndtimeMixin
from pysmo.lib.io import (
    extract_geocsv_timeseries,
    merge_geocsv_timeseries,
    parse_geocsv,
)
from pysmo.lib.validators import (
    convert_to_ndarray,
    convert_to_timedelta,
    convert_to_utc_timestamp,
)
from pysmo.typing import PositiveTimedelta, UtcTimestamp

__all__ = ["GeoCsvSeismogram"]


@define(kw_only=True)
class GeoCsvSeismogram(SeismogramEndtimeMixin):
    """Import class for seismograms in the GeoCSV timeseries format.

    Reads a waveform from the timeseries flavour of
    [GeoCSV](https://ds.iris.edu/files/documents/GeoCSV.pdf) and exposes
    it as a [`Seismogram`][pysmo.Seismogram]-compatible object.

    This class is intended as a data-ingestion step. Once loaded, use
    [`clone_to_mini`][pysmo.functions.clone_to_mini] to convert the
    waveform to a [`MiniSeismogram`][pysmo.MiniSeismogram], which can then
    be passed to [`copy_from_mini`][pysmo.functions.copy_from_mini] to
    populate another object such as a [`SAC`][pysmo.classes.SAC] instance.
    Instances can be modified in memory but there is no write-back to
    GeoCSV.

    Examples:
        ```python
        >>> from pysmo import Seismogram
        >>> from pysmo.classes import GeoCsvSeismogram
        >>> text = '''\\
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
        >>> isinstance(seismogram, Seismogram)
        True
        >>> seismogram.sid
        'IU_ANMO_00_LHZ'
        >>> seismogram.data
        array([-47297., -47298., -47299.])
        >>> seismogram.end_time
        Timestamp('2010-02-27 06:30:02+0000', tz='UTC')
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
        converter=convert_to_ndarray,
        validator=validators.instance_of(np.ndarray),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Seismogram data."""

    sid: str = field(
        validator=validators.instance_of(str),
        on_setattr=setters.validate,
    )
    """FDSN source identifier of the parsed GeoCSV data (e.g. `IU_ANMO_00_LHZ`).

    This is parse-time metadata: it describes the GeoCSV data the instance
    was created from and is not updated when other attributes change.
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
            sid=segment.sid,
        )
