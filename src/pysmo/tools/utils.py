"""Pysmo's little helpers."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID
import numpy as np


def average_datetimes(datetimes: Sequence[datetime]) -> datetime:
    """Average a sequence of datetimes.

    Args:
        datetimes: Datetimes to average.

    Returns:
        Datetime representing average of all datetimes.

    Raises:
        ValueError: If an empty sequence is provides as input.
    """
    if len(datetimes) == 0:
        raise ValueError("Cannot average empty sequence of datetimes.")
    reference_time = datetimes[0]
    seconds = sum((i - reference_time).total_seconds() for i in datetimes[1:])
    return reference_time + timedelta(seconds=seconds / len(datetimes))


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
