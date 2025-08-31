import pytest
from numpy import mean
from numpy.random import uniform


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
