from typing import Protocol
import numpy as np
import datetime


class Seismogram(Protocol):
    """The :class:`Seismogram` class defines a protocol for a basic seismogram as used in pysmo.

    Example usage for a function that takes a Seismogram compatible class instance as argument
    and returns the begin time in isoformat::

        >>> from pysmo import SAC, Seismogram  # SAC is a class that "speaks" Seismogram
        >>> def begin_time_in_isoformat(seis_in: Seismogram) -> str:
        ...     return seis_in.begin_time.isoformat()
        ...
        >>> my_sac = SAC.from_file('testfile.sac')
        >>> example_function(my_sac)
        '2005-03-02T07:23:02.160000'
    """
    def __len__(self) -> int:
        ...

    @property
    def data(self) -> np.ndarray:
        """Returns the seismogram data as numpy array."""
        ...

    @data.setter
    def data(self, value: np.ndarray) -> None:
        """Sets the data."""
        ...

    @property
    def begin_time(self) -> datetime.datetime:
        """Returns the begin time"""
        ...

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
        """Returns the begin time"""
        ...

    @property
    def end_time(self) -> datetime.datetime:
        """Returns the end time"""
        ...

    @property
    def sampling_rate(self) -> float:
        """Returns sampling rate."""
        ...

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        """Sets the sampling rate."""
        ...
