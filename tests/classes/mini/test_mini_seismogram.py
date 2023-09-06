import numpy as np
import numpy.testing as npt
import pytest
from datetime import datetime, timedelta, timezone
from pysmo import Seismogram, MiniSeismogram, SAC
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS


class TestMiniSeismogram:

    def test_create_instance(self) -> None:
        """Test creating an instance."""

        miniseis = MiniSeismogram()
        assert isinstance(miniseis, MiniSeismogram)
        assert isinstance(miniseis, Seismogram)

    @pytest.mark.depends(name='test_create_instance')
    def test_defaults(self) -> None:
        """Test default attributes."""

        miniseis = MiniSeismogram()
        assert miniseis.begin_time.year == SEISMOGRAM_DEFAULTS.begin_time.year == 1970
        assert miniseis.begin_time.month == SEISMOGRAM_DEFAULTS.begin_time.month == 1
        assert miniseis.begin_time.day == SEISMOGRAM_DEFAULTS.begin_time.day == 1
        assert miniseis.begin_time.hour == SEISMOGRAM_DEFAULTS.begin_time.hour == 0
        assert miniseis.begin_time.minute == SEISMOGRAM_DEFAULTS.begin_time.minute == 0
        assert miniseis.begin_time.second == SEISMOGRAM_DEFAULTS.begin_time.second == 0
        assert miniseis.begin_time.microsecond == SEISMOGRAM_DEFAULTS.begin_time.microsecond == 0
        assert miniseis.sampling_rate == SEISMOGRAM_DEFAULTS.sampling_rate == 1
        assert miniseis.data.size == 0
        assert len(miniseis) == 0
        assert miniseis.id is None

    @pytest.mark.depends(name='test_create_instance')
    def test_change_attributes(self) -> None:

        miniseis = MiniSeismogram()
        random_data = np.random.rand(1000)
        new_time = datetime.fromisoformat('2011-11-04T00:05:23.123')
        miniseis.data = random_data
        assert miniseis.data.all() == random_data.all()
        assert miniseis.end_time - miniseis.begin_time == timedelta(
            seconds=miniseis.sampling_rate * (len(miniseis)-1))
        miniseis.begin_time = new_time
        assert miniseis.begin_time == new_time
        assert miniseis.end_time - miniseis.begin_time == timedelta(
            seconds=miniseis.sampling_rate * (len(miniseis)-1))
        miniseis.sampling_rate = 0.1
        assert miniseis.sampling_rate == 0.1
        assert miniseis.end_time - miniseis.begin_time == timedelta(
            seconds=miniseis.sampling_rate * (len(miniseis)-1))
        miniseis.id = 'test'
        assert miniseis.id == 'test'

    @pytest.mark.depends(name='test_change_attributes')
    def test_as_seismogram(self) -> None:
        """check if it works in a functionfor Seismogram types."""

        def seis_func(seismogram: Seismogram) -> None:

            _ = len(seismogram)
            _ = np.mean(seismogram.data)
            _ = seismogram.sampling_rate * 1.1
            _ = seismogram.begin_time + timedelta(seconds=12)
            _ = seismogram.end_time + timedelta(seconds=12)

        miniseis = MiniSeismogram(data=np.random.rand(1000))
        seis_func(miniseis)


class TestMiniSeismogramMethods:

    @pytest.fixture
    def mini_seismogram(self) -> MiniSeismogram:
        return MiniSeismogram(data=np.random.rand(1000))

    def test_clone(self) -> None:
        # create sac seismogram and add data
        data = np.random.rand(1000)
        sac_seis = SAC().seismogram
        sac_seis.data = data
        sac_seis.sampling_rate = 0.1
        sac_seis.begin_time = datetime.now(timezone.utc)

        # clone and check attributes are identical
        mini_seis = MiniSeismogram.clone(sac_seis)
        npt.assert_allclose(sac_seis.data, mini_seis.data)
        assert sac_seis.data is not mini_seis.data
        assert sac_seis.begin_time == mini_seis.begin_time
        assert sac_seis.begin_time is not mini_seis.begin_time
        assert sac_seis.sampling_rate == mini_seis.sampling_rate
        assert sac_seis.end_time == mini_seis.end_time

        # verify changes in clone don't affect input seismogram
        mini_seis.data[0] *= 2
        with npt.assert_raises(AssertionError):
            npt.assert_allclose(sac_seis.data, mini_seis.data)
        mini_seis.begin_time = datetime.now(timezone.utc)
        assert sac_seis.begin_time != mini_seis.begin_time
        mini_seis.sampling_rate *= 2
        assert sac_seis.sampling_rate != mini_seis.sampling_rate
        assert sac_seis.end_time != mini_seis.end_time

        # create clone without data
        mini_seis = MiniSeismogram.clone(sac_seis, skip_data=True)
        npt.assert_allclose(mini_seis.data, np.array([]))

    def test_normalize(self, mini_seismogram: MiniSeismogram) -> None:
        mini_seismogram.normalize()
        assert np.max(mini_seismogram.data) <= 1

    def test_detrend(self, mini_seismogram: MiniSeismogram) -> None:
        mini_seismogram.detrend()
        assert 0 == pytest.approx(np.mean(mini_seismogram.data), abs=1e-11)

    def test_resample(self, mini_seismogram: MiniSeismogram) -> None:
        old_sampling_rate = mini_seismogram.sampling_rate
        old_len = len(mini_seismogram)
        new_sampling_rate = old_sampling_rate * 2
        mini_seismogram.resample(new_sampling_rate)
        assert len(mini_seismogram) * 2 == old_len
        assert mini_seismogram.sampling_rate == new_sampling_rate
