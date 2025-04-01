import numpy as np
import pytest
from datetime import datetime, timedelta, timezone
from pysmo import Seismogram, MiniSeismogram
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS


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
        assert miniseis.begin_time.tzinfo == SEISMOGRAM_DEFAULTS.begin_time.value.tzinfo
        assert (
            miniseis.begin_time.year
            == SEISMOGRAM_DEFAULTS.begin_time.value.year
            == 1970
        )
        assert (
            miniseis.begin_time.month == SEISMOGRAM_DEFAULTS.begin_time.value.month == 1
        )
        assert miniseis.begin_time.day == SEISMOGRAM_DEFAULTS.begin_time.value.day == 1
        assert (
            miniseis.begin_time.hour == SEISMOGRAM_DEFAULTS.begin_time.value.hour == 0
        )
        assert (
            miniseis.begin_time.minute
            == SEISMOGRAM_DEFAULTS.begin_time.value.minute
            == 0
        )
        assert (
            miniseis.begin_time.second
            == SEISMOGRAM_DEFAULTS.begin_time.value.second
            == 0
        )
        assert (
            miniseis.begin_time.microsecond
            == SEISMOGRAM_DEFAULTS.begin_time.value.microsecond
            == 0
        )
        assert miniseis.delta == SEISMOGRAM_DEFAULTS.delta.value == timedelta(seconds=1)
        assert miniseis.data.size == 0
        assert len(miniseis) == 0

    @pytest.mark.depends(name="test_create_instance")
    def test_change_attributes(self) -> None:
        miniseis = MiniSeismogram()
        random_data = np.random.rand(1000)
        new_time_no_tz = datetime.fromisoformat("2011-11-04T00:05:23.123")
        new_time_utc = datetime.fromisoformat("2011-11-04T00:05:23.123").replace(
            tzinfo=timezone.utc
        )
        miniseis.data = random_data
        assert miniseis.data.all() == random_data.all()
        assert miniseis.end_time - miniseis.begin_time == miniseis.delta * (
            len(miniseis) - 1
        )
        miniseis.begin_time = new_time_utc
        assert miniseis.begin_time == new_time_utc
        assert miniseis.end_time - miniseis.begin_time == miniseis.delta * (
            len(miniseis) - 1
        )
        miniseis.delta = timedelta(seconds=0.1)
        assert miniseis.delta.total_seconds() == 0.1
        assert miniseis.end_time - miniseis.begin_time == miniseis.delta * (
            len(miniseis) - 1
        )
        with pytest.raises(TypeError):
            miniseis.begin_time = new_time_no_tz

    @pytest.mark.depends(name="test_change_attributes")
    def test_as_seismogram(self) -> None:
        """check if it works in a functionfor Seismogram types."""

        def seis_func(seismogram: Seismogram) -> None:
            _ = len(seismogram)
            _ = np.mean(seismogram.data)
            _ = seismogram.delta * 1.1
            _ = seismogram.begin_time + timedelta(seconds=12)
            _ = seismogram.end_time + timedelta(seconds=12)

        miniseis = MiniSeismogram(data=np.random.rand(1000))
        seis_func(miniseis)
