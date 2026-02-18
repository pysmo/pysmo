from pandas import Timestamp, Timedelta
from datetime import timezone
import pytest
from pysmo import Event, MiniEvent


class TestMiniEvent:
    def test_create_instance(self) -> None:
        """Test creating an instance."""

        # shouldn'b be able to create an instance with kwargs
        with pytest.raises(TypeError):
            minievent = MiniEvent()  # type: ignore
        latitude, longitude = (
            1.1,
            2.2,
        )
        depth = 1000
        time_utc, time_no_tz = Timestamp.now(timezone.utc), Timestamp.now()
        minievent = MiniEvent(
            latitude=latitude, longitude=longitude, depth=depth, time=time_utc
        )
        with pytest.raises(TypeError):
            minievent = MiniEvent(
                latitude=latitude, longitude=longitude, depth=depth, time=time_no_tz
            )
        assert isinstance(minievent, MiniEvent)
        assert isinstance(minievent, Event)

    @pytest.mark.depends(name="test_create_instance")
    def test_change_attributes(self) -> None:
        latitude, longitude, depth, time = 1.1, 2.2, 1000, Timestamp.now(timezone.utc)
        new_latitude, new_longitude, new_depth, new_time = (
            -21.1,
            -22.2,
            500.2,
            time + Timedelta(minutes=3),
        )

        minievent = MiniEvent(
            latitude=latitude, longitude=longitude, depth=depth, time=time
        )

        assert isinstance(minievent, Event)

        assert minievent.depth == depth
        assert minievent.latitude == latitude
        assert minievent.longitude == longitude
        assert minievent.time == time

        minievent.depth = new_depth
        assert minievent.depth == new_depth
        minievent.latitude = new_latitude
        assert minievent.latitude == new_latitude
        minievent.longitude = new_longitude
        assert minievent.longitude == new_longitude
        minievent.time = new_time
        assert minievent.time == new_time

        with pytest.raises(ValueError):
            minievent.latitude = -100
        with pytest.raises(ValueError):
            minievent.latitude = 100
        with pytest.raises(ValueError):
            minievent.longitude = -180
        with pytest.raises(ValueError):
            minievent.latitude = 181
