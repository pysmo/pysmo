"""Pysmo's little helpers."""

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID
import numpy as np
import numpy.typing as npt


def to_seconds(td: timedelta | np.timedelta64) -> float:
    """Convert timedelta or timedelta64 to seconds as float.

    This function handles both Python timedelta and numpy timedelta64 objects,
    converting them to seconds as a float value.

    Args:
        td: Timedelta to convert (either Python timedelta or numpy timedelta64).

    Returns:
        Time duration in seconds as float.

    Examples:
        ```python
        >>> from datetime import timedelta
        >>> import numpy as np
        >>> from pysmo.tools.utils import to_seconds
        >>>
        >>> # With Python timedelta
        >>> td = timedelta(seconds=1.5)
        >>> to_seconds(td)
        1.5
        >>>
        >>> # With numpy timedelta64
        >>> td64 = np.timedelta64(1_500_000, 'us')
        >>> to_seconds(td64)
        1.5
        >>>
        ```
    """
    if isinstance(td, timedelta):
        return td.total_seconds()
    else:
        # numpy timedelta64
        return td.astype("timedelta64[us]").astype(np.int64) / 1_000_000.0


def datetimes_to_datetime64(
def datetimes_to_datetime64(
    datetimes: Sequence[datetime],
) -> npt.NDArray[np.datetime64]:
    """Convert a sequence of datetime objects to numpy datetime64 array.

    If a datetime has no tzinfo, it is assumed to be UTC. If a datetime
    has tzinfo, it is converted to UTC before converting to datetime64.

    Args:
        datetimes: Sequence of datetime objects to convert.

    Returns:
        NumPy array of datetime64[us] objects in UTC.

    Raises:
        ValueError: If an empty sequence is provided as input.

    Examples:
        ```python
        >>> from datetime import datetime, timezone
        >>> from pysmo.tools.utils import datetimes_to_datetime64
        >>>
        >>> # Create some datetimes
        >>> dt1 = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> dt2 = datetime(2020, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        >>>
        >>> # Convert to datetime64
        >>> dt64_array = datetimes_to_datetime64([dt1, dt2])
        >>> dt64_array
        array(['2020-01-01T12:00:00.000000', '2020-01-02T12:00:00.000000'],
              dtype='datetime64[us]')
        >>>
        ```
    """
    if len(datetimes) == 0:
        raise ValueError("Cannot convert empty sequence of datetimes.")

    # Convert datetimes to UTC timestamps (as microseconds since epoch)
    utc_timestamps = []
    for dt in datetimes:
        if dt.tzinfo is None:
            # Assume UTC
            utc_dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            utc_dt = dt.astimezone(timezone.utc)
        # Convert to microseconds since epoch
        us_since_epoch = int(utc_dt.timestamp() * 1_000_000)
        utc_timestamps.append(us_since_epoch)

    # Create datetime64 array from microseconds since epoch
    return np.array(utc_timestamps, dtype="int64").astype("datetime64[us]")


def datetime64_to_datetimes(
    datetime64_array: npt.NDArray[np.datetime64],
) -> list[datetime]:
    """Convert a numpy datetime64 array to a list of datetime objects.

    The resulting datetime objects are always in UTC timezone.

    Args:
        datetime64_array: NumPy array of datetime64 objects.

    Returns:
        List of datetime objects in UTC.

    Raises:
        ValueError: If an empty array is provided as input.

    Examples:
        ```python
        >>> from datetime import datetime, timezone
        >>> from pysmo.tools.utils import (
        ...     datetimes_to_datetime64,
        ...     datetime64_to_datetimes,
        ... )
        >>>
        >>> # Create some datetimes
        >>> dt1 = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> dt2 = datetime(2020, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        >>>
        >>> # Convert to datetime64 and back
        >>> dt64_array = datetimes_to_datetime64([dt1, dt2])
        >>> result = datetime64_to_datetimes(dt64_array)
        >>> result[0] == dt1
        True
        >>> result[1] == dt2
        True
        >>>
        ```
    """
    if len(datetime64_array) == 0:
        raise ValueError("Cannot convert empty array of datetime64 objects.")

    # Convert to Python datetime objects with UTC timezone
    result = []
    for dt64 in datetime64_array:
        # Convert to timestamp and create datetime
        timestamp = dt64.astype("datetime64[us]").astype(np.int64) / 1_000_000
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        result.append(dt)

    return result


def timedeltas_to_timedelta64(
    timedeltas: Sequence[timedelta],
) -> npt.NDArray[np.timedelta64]:
    """Convert a sequence of timedelta objects to numpy timedelta64 array.

    Args:
        timedeltas: Sequence of timedelta objects to convert.

    Returns:
        NumPy array of timedelta64[us] objects.

    Raises:
        ValueError: If an empty sequence is provided as input.

    Examples:
        ```python
        >>> from datetime import timedelta
        >>> from pysmo.tools.utils import timedeltas_to_timedelta64
        >>>
        >>> # Create some timedeltas
        >>> td1 = timedelta(seconds=1.5)
        >>> td2 = timedelta(seconds=2.5)
        >>>
        >>> # Convert to timedelta64
        >>> td64_array = timedeltas_to_timedelta64([td1, td2])
        >>> td64_array
        array([1500000, 2500000], dtype='timedelta64[us]')
        >>>
        ```
    """
    if len(timedeltas) == 0:
        raise ValueError("Cannot convert empty sequence of timedeltas.")

    # Convert timedeltas to microseconds
    us_values = [int(to_seconds(td) * 1_000_000) for td in timedeltas]
    return np.array(us_values, dtype="timedelta64[us]")


def timedelta64_to_timedeltas(
    timedelta64_array: npt.NDArray[np.timedelta64],
) -> list[timedelta]:
    """Convert a numpy timedelta64 array to a list of timedelta objects.

    Args:
        timedelta64_array: NumPy array of timedelta64 objects.

    Returns:
        List of timedelta objects.

    Raises:
        ValueError: If an empty array is provided as input.

    Examples:
        ```python
        >>> from datetime import timedelta
        >>> from pysmo.tools.utils import (
        ...     timedeltas_to_timedelta64,
        ...     timedelta64_to_timedeltas,
        ... )
        >>>
        >>> # Create some timedeltas
        >>> td1 = timedelta(seconds=1.5)
        >>> td2 = timedelta(seconds=2.5)
        >>>
        >>> # Convert to timedelta64 and back
        >>> td64_array = timedeltas_to_timedelta64([td1, td2])
        >>> result = timedelta64_to_timedeltas(td64_array)
        >>> result[0] == td1
        True
        >>> result[1] == td2
        True
        >>>
        ```
    """
    if len(timedelta64_array) == 0:
        raise ValueError("Cannot convert empty array of timedelta64 objects.")

    # Convert to Python timedelta objects
    result = []
    for td64 in timedelta64_array:
        # Convert to microseconds and create timedelta
        us = td64.astype("timedelta64[us]").astype(np.int64)
        td = timedelta(microseconds=int(us))
        result.append(td)

    return result


def average_datetimes(datetimes: Sequence[datetime]) -> datetime:
    """Average a sequence of datetimes.

    Args:
        datetimes: Datetimes to average.

    Returns:
        Datetime representing average of all datetimes.

    Raises:
        ValueError: If an empty sequence is provided as input.

    Examples:
        ```python
        >>> from datetime import datetime, timezone
        >>> from pysmo.tools.utils import average_datetimes
        >>>
        >>> # Create some datetimes
        >>> dt1 = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        >>> dt2 = datetime(2020, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        >>> dt3 = datetime(2020, 1, 3, 12, 0, 0, tzinfo=timezone.utc)
        >>>
        >>> # Average them
        >>> result = average_datetimes([dt1, dt2, dt3])
        >>> result
        datetime.datetime(2020, 1, 2, 12, 0, tzinfo=datetime.timezone.utc)
        >>>
        ```
    """
    if len(datetimes) == 0:
        raise ValueError("Cannot average empty sequence of datetimes.")

    # Use numpy datetime64 for efficient averaging
    dt64_array = datetimes_to_datetime64(datetimes)
    avg_dt64 = dt64_array.astype("datetime64[us]").view("int64").mean()
    avg_dt64 = np.datetime64(int(avg_dt64), "us")

    # Convert back to datetime
    return datetime64_to_datetimes(np.array([avg_dt64]))[0]


def uuid_shortener(uuids: Sequence[UUID], min_length: int = 4) -> dict[str, UUID]:
    """Shorten a sequence of UUIDs to their shortest unique representation.

    Args:
        uuids: UUIDs to shorten.
        min_length: Minimum length of the shortened UUID strings.

    Returns:
        Dictionary mapping shortened UUID strings to their original UUID objects.

    Raises:
        ValueError: If an empty sequence is provided as input.
        ValueError: If `min_length` is not between 1 and 36.

    Examples:
        ```python
        >>> import uuid
        >>> from pysmo.tools.utils import uuid_shortener
        >>>
        >>> uuids = [uuid.uuid4() for _ in range(100)]
        >>> for k, v in sorted(uuid_shortener(uuids).items()):
        ...     print(f"{k} -> {v}")
        ...
        01d7 -> 01d74256-3860-4ab6-96a4-02f23ae8cc93
        03c7 -> 03c72ba8-d605-4770-8a63-f881ffd0f9d5
        080a -> 080aadfb-e7c9-4b26-9141-25c63a9bedd4
        0e51 -> 0e51f30d-c6a7-4e39-84b0-32ccd7c524a5
        ...
        >>>
        ```
    """
    UUID_LENGTH = 36

    if len(uuids) == 0:
        raise ValueError("Cannot shorten empty sequence of UUIDs.")

    if not (1 <= min_length <= UUID_LENGTH):
        raise ValueError(f"min_length must be between 1 and {UUID_LENGTH}.")

    for length in range(min_length, UUID_LENGTH + 1):
        shortened = [u[:length] for u in map(str, uuids)]
        if len(set(shortened)) == len(uuids):
            return {u: uuid for u, uuid in zip(shortened, uuids)}

    # Fallback to full UUIDs if necessary (like that's going to happen...)
    return {str(u): u for u in uuids}


def pearson_matrix_vector(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Compute Pearson correlation of each row in a matrix against a vector.

    This is a vectorized alternative to calling
    [`scipy.stats.pearsonr`][scipy.stats.pearsonr] in a loop. All row
    correlations are computed in a single matrix operation.

    Args:
        matrix: 2D array of shape `(N, M)` where each row is correlated
            against `vector`.
        vector: 1D array of length `M`.

    Returns:
        1D array of length `N` with Pearson correlation coefficients.

    Raises:
        ValueError: If `matrix` is not 2D or `vector` is not 1D.
        ValueError: If the number of columns in `matrix` does not match the
            length of `vector`.

    Examples:
        ```python
        >>> import numpy as np
        >>> from pysmo.tools.utils import pearson_matrix_vector
        >>>
        >>> vector = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        >>> matrix = np.array([
        ...     [1.0, 2.0, 3.0, 4.0, 5.0],
        ...     [5.0, 4.0, 3.0, 2.0, 1.0],
        ...     [1.0, 1.0, 1.0, 1.0, 1.0],
        ... ])
        >>> pearson_matrix_vector(matrix, vector)
        array([ 1., -1.,  0.])
        >>>
        ```
    """
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D, got {matrix.ndim}D.")
    if vector.ndim != 1:
        raise ValueError(f"vector must be 1D, got {vector.ndim}D.")
    if matrix.shape[1] != vector.shape[0]:
        raise ValueError(
            f"Shape mismatch: matrix has {matrix.shape[1]} columns "
            f"but vector has {vector.shape[0]} elements."
        )

    matrix_dm = matrix - matrix.mean(axis=1, keepdims=True)
    vector_dm = vector - vector.mean()
    numer = matrix_dm @ vector_dm
    denom = np.sqrt((matrix_dm**2).sum(axis=1) * (vector_dm**2).sum())
    # Rows with zero std produce 0/0; return 0 for those.
    return np.divide(numer, denom, out=np.zeros_like(numer), where=denom != 0)
