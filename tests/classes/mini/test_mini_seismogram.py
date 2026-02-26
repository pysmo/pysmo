import numpy as np
import pytest
from pandas import Timestamp, Timedelta
from datetime import timezone
from pysmo import Seismogram, MiniSeismogram
from pysmo.lib.defaults import SeismogramDefaults


class TestMiniSeismogram:
    def test_create_instance(self) -> None:
        """Test creating an instance."""

        miniseis = MiniSeismogram()
        assert isinstance(miniseis, MiniSeismogram)
        assert isinstance(miniseis, Seismogram)

    @pytest.mark.depends(name="test_create_instance")
    def test_defaults(self) -> None:
        """Test default attributes."""

        miniseis = MiniSeismogram()
        assert miniseis.begin_time.tzinfo == SeismogramDefaults.begin_time.tzinfo
        assert miniseis.begin_time.year == SeismogramDefaults.begin_time.year == 1970
        assert miniseis.begin_time.month == SeismogramDefaults.begin_time.month == 1
        assert miniseis.begin_time.day == SeismogramDefaults.begin_time.day == 1
        assert miniseis.begin_time.hour == SeismogramDefaults.begin_time.hour == 0
        assert miniseis.begin_time.minute == SeismogramDefaults.begin_time.minute == 0
        assert miniseis.begin_time.second == SeismogramDefaults.begin_time.second == 0
        assert (
            miniseis.begin_time.microsecond
            == SeismogramDefaults.begin_time.microsecond
            == 0
        )
        assert miniseis.delta == SeismogramDefaults.delta == Timedelta(seconds=1)
        assert miniseis.data.size == 0
        assert len(miniseis.data) == 0

    @pytest.mark.depends(name="test_create_instance")
    def test_change_attributes(self) -> None:
        miniseis = MiniSeismogram()
        random_data = np.random.rand(1000)
        new_time_no_tz = Timestamp.fromisoformat("2011-11-04T00:05:23.123")
        new_time_utc = Timestamp.fromisoformat("2011-11-04T00:05:23.123").replace(
            tzinfo=timezone.utc
        )
        miniseis.data = random_data
        assert miniseis.data.all() == random_data.all()
        assert miniseis.end_time - miniseis.begin_time == miniseis.delta * (
            len(miniseis.data) - 1
        )
        miniseis.begin_time = new_time_utc
        assert miniseis.begin_time == new_time_utc
        assert miniseis.end_time - miniseis.begin_time == miniseis.delta * (
            len(miniseis.data) - 1
        )
        miniseis.delta = Timedelta(seconds=0.1)
        assert miniseis.delta.total_seconds() == 0.1
        assert miniseis.end_time - miniseis.begin_time == miniseis.delta * (
            len(miniseis.data) - 1
        )
        with pytest.raises(TypeError):
            miniseis.begin_time = new_time_no_tz

        miniseis.data = np.array([])
        assert len(miniseis.data) == 0
        assert miniseis.begin_time == miniseis.end_time

    @pytest.mark.depends(name="test_change_attributes")
    def test_as_seismogram(self) -> None:
        """check if it works in a functionfor Seismogram types."""

        def seis_func(seismogram: Seismogram) -> None:
            _ = len(seismogram.data)
            _ = np.mean(seismogram.data)
            _ = seismogram.delta * 1.1
            _ = seismogram.begin_time + Timedelta(seconds=12)
            _ = seismogram.end_time + Timedelta(seconds=12)

        miniseis = MiniSeismogram(data=np.random.rand(1000))
        seis_func(miniseis)
