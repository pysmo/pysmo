from datetime import timezone

import pandas as pd
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
        time_utc = pd.Timestamp.now(timezone.utc)
        minievent = MiniEvent(
            latitude=latitude, longitude=longitude, depth=depth, time=time_utc
        )
        assert isinstance(minievent, MiniEvent)
        assert isinstance(minievent, Event)

    @pytest.mark.depends(name="test_create_instance")
    def test_change_attributes(self) -> None:
        latitude, longitude, depth, time = (
            1.1,
            2.2,
            1000,
            pd.Timestamp.now(timezone.utc),
        )
        new_latitude, new_longitude, new_depth, new_time = (
            -21.1,
            -22.2,
            500.2,
            time + pd.Timedelta(minutes=3),
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

        # Test time conversion on set
        minievent.time = "2024-03-03T12:00:00"  # type: ignore
        assert isinstance(minievent.time, pd.Timestamp)
        assert minievent.time.tzinfo == timezone.utc

        with pytest.raises(ValueError):
            minievent.latitude = -100
        with pytest.raises(ValueError):
            minievent.latitude = 100
        with pytest.raises(ValueError):
            minievent.longitude = -180
        with pytest.raises(ValueError):
            minievent.longitude = 181

        # Test conversion on set
        minievent.depth = "123.4"  # type: ignore
        assert minievent.depth == 123.4
        with pytest.raises(ValueError):
            minievent.depth = "abc"  # type: ignore
