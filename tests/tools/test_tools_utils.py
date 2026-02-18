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


def test_average_datetimes() -> None:
    from pysmo.tools.utils import average_datetimes
    from datetime import datetime, timedelta, timezone

    with pytest.raises(ValueError):
        average_datetimes([])
    now = datetime.now(timezone.utc)
    assert average_datetimes([now]) == now

    now_no_tz = datetime.now()
    with pytest.raises(TypeError):
        average_datetimes([now, now_no_tz])

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
