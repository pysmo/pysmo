from numpy import mean
from numpy.random import uniform
import numpy as np
import random as rd
import pytest


@pytest.fixture()
def mock_uuid4(monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid

    rand = rd.Random()
    rand.seed(42)
    monkeypatch.setattr(
        uuid, "uuid4", lambda: uuid.UUID(int=rand.getrandbits(128), version=4)
    )


def test_to_seconds() -> None:
    from pysmo.tools.utils import to_seconds
    from datetime import timedelta
    import numpy as np

    # Test with Python timedelta
    td = timedelta(seconds=1.5)
    assert to_seconds(td) == 1.5

    # Test with numpy timedelta64
    td64 = np.timedelta64(1_500_000, "us")
    assert to_seconds(td64) == 1.5

    # Test with various values
    assert to_seconds(timedelta(seconds=10)) == 10.0
    assert to_seconds(timedelta(microseconds=500_000)) == 0.5
    assert to_seconds(np.timedelta64(2_000_000, "us")) == 2.0
    assert to_seconds(np.timedelta64(0, "us")) == 0.0
    assert to_seconds(np.timedelta64(-1_000_000, "us")) == -1.0


def test_datetimes_to_datetime64() -> None:
    from pysmo.tools.utils import datetimes_to_datetime64
    from datetime import datetime, timezone

    # Test with empty sequence
    with pytest.raises(ValueError, match="empty sequence"):
        datetimes_to_datetime64([])

    # Test with UTC datetimes
    dt1 = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2020, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    result = datetimes_to_datetime64([dt1, dt2])
    assert result.dtype == np.dtype("datetime64[us]")
    assert len(result) == 2

    # Test with naive datetime (assumed to be UTC)
    dt_naive = datetime(2020, 1, 1, 12, 0, 0)
    result_naive = datetimes_to_datetime64([dt_naive])
    assert result_naive.dtype == np.dtype("datetime64[us]")


def test_datetime64_to_datetimes() -> None:
    from pysmo.tools.utils import (
        datetimes_to_datetime64,
        datetime64_to_datetimes,
    )
    from datetime import datetime, timezone

    # Test with empty array
    with pytest.raises(ValueError, match="empty array"):
        datetime64_to_datetimes(np.array([], dtype="datetime64[us]"))

    # Test round-trip conversion
    dt1 = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2020, 1, 2, 12, 30, 45, 123456, tzinfo=timezone.utc)
    original = [dt1, dt2]
    dt64_array = datetimes_to_datetime64(original)
    result = datetime64_to_datetimes(dt64_array)

    assert len(result) == 2
    assert result[0] == dt1
    assert result[1] == dt2
    assert all(dt.tzinfo == timezone.utc for dt in result)


def test_timedeltas_to_timedelta64() -> None:
    from pysmo.tools.utils import timedeltas_to_timedelta64
    from datetime import timedelta

    # Test with empty sequence
    with pytest.raises(ValueError, match="empty sequence"):
        timedeltas_to_timedelta64([])

    # Test with timedeltas
    td1 = timedelta(seconds=1.5)
    td2 = timedelta(seconds=2.5)
    result = timedeltas_to_timedelta64([td1, td2])
    assert result.dtype == np.dtype("timedelta64[us]")
    assert len(result) == 2


def test_timedelta64_to_timedeltas() -> None:
    from pysmo.tools.utils import (
        timedeltas_to_timedelta64,
        timedelta64_to_timedeltas,
    )
    from datetime import timedelta

    # Test with empty array
    with pytest.raises(ValueError, match="empty array"):
        timedelta64_to_timedeltas(np.array([], dtype="timedelta64[us]"))

    # Test round-trip conversion
    td1 = timedelta(seconds=1.5)
    td2 = timedelta(seconds=2.5)
    td3 = timedelta(microseconds=123456)
    original = [td1, td2, td3]
    td64_array = timedeltas_to_timedelta64(original)
    result = timedelta64_to_timedeltas(td64_array)

    assert len(result) == 3
    assert result[0] == td1
    assert result[1] == td2
    assert result[2] == td3


def test_average_datetimes() -> None:
    from pysmo.tools.utils import average_datetimes
    from datetime import datetime, timedelta, timezone

    with pytest.raises(ValueError):
        average_datetimes([])
    now = datetime.now(timezone.utc)
    assert average_datetimes([now]) == now

    # Test with naive datetime (assumed to be UTC in new implementation)
    now_no_tz = datetime.now()
    # This should now work by assuming UTC
    result = average_datetimes([now_no_tz])
    assert result.tzinfo == timezone.utc

    random_seconds = uniform(low=-1000, high=1000, size=1000)
    random_times = [now + timedelta(seconds=i) for i in random_seconds]
    assert average_datetimes(random_times).timestamp() == pytest.approx(
        (now + timedelta(seconds=float(mean(random_seconds)))).timestamp()
    )


def test_uuid_shortener(mock_uuid4, snapshot) -> None:  # type: ignore
    from pysmo.tools.utils import uuid_shortener
    import uuid

    uuids = [uuid.uuid4() for _ in range(1000)]

    view = sorted(uuid_shortener(uuids).items())
    assert view == snapshot

    # simulate collision (which in our case means shortening is not possible)
    uuids.append(uuids[0])
    assert all(len(k) == 36 for k in uuid_shortener(uuids).keys())

    with pytest.raises(ValueError):
        uuid_shortener([])

    with pytest.raises(ValueError):
        uuid_shortener(uuids, min_length=0)


def test_pearson_matrix_vector_perfect_correlation() -> None:
    from pysmo.tools.utils import pearson_matrix_vector

    vector = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    matrix = np.array(
        [
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [5.0, 4.0, 3.0, 2.0, 1.0],
        ]
    )
    result = pearson_matrix_vector(matrix, vector)
    np.testing.assert_allclose(result, [1.0, -1.0])


def test_pearson_matrix_vector_against_scipy() -> None:
    from pysmo.tools.utils import pearson_matrix_vector
    from scipy.stats import pearsonr

    rng = np.random.default_rng(42)
    vector = rng.standard_normal(200)
    matrix = rng.standard_normal((50, 200))

    result = pearson_matrix_vector(matrix, vector)
    expected = np.array([pearsonr(row, vector).statistic for row in matrix])
    np.testing.assert_allclose(result, expected, atol=1e-12)


def test_pearson_matrix_vector_constant_row() -> None:
    from pysmo.tools.utils import pearson_matrix_vector

    vector = np.array([1.0, 2.0, 3.0])
    matrix = np.array(
        [
            [1.0, 2.0, 3.0],
            [5.0, 5.0, 5.0],
        ]
    )
    result = pearson_matrix_vector(matrix, vector)
    assert result[0] == pytest.approx(1.0)
    assert result[1] == pytest.approx(0.0)


def test_pearson_matrix_vector_shape_errors() -> None:
    from pysmo.tools.utils import pearson_matrix_vector

    with pytest.raises(ValueError, match="2D"):
        pearson_matrix_vector(np.array([1.0, 2.0]), np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="1D"):
        pearson_matrix_vector(np.ones((2, 3)), np.ones((2, 3)))
    with pytest.raises(ValueError, match="Shape mismatch"):
        pearson_matrix_vector(np.ones((2, 3)), np.ones(4))
