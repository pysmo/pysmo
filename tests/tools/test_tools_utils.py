from numpy import mean
from numpy.random import uniform
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
