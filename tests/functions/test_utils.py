from pysmo import MiniSeismogram, MiniStation
from pysmo.classes import SAC
import numpy.testing as npt
import pytest


class TestUtilsFunctions:
    def test_clone_to_mini(
        self, sac_instance: SAC, mini_seismogram: MiniSeismogram
    ) -> None:
        from pysmo.functions import clone_to_mini

        # clone miniseis
        mini_clone = clone_to_mini(MiniSeismogram, mini_seismogram)
        assert mini_clone.begin_time == mini_seismogram.begin_time
        assert mini_clone.delta == mini_seismogram.delta
        npt.assert_equal(mini_clone.data, mini_seismogram.data)

        # clone sac
        mini_clone = clone_to_mini(MiniSeismogram, sac_instance.seismogram)
        assert mini_clone.begin_time == sac_instance.seismogram.begin_time
        assert mini_clone.delta == sac_instance.seismogram.delta
        npt.assert_equal(mini_clone.data, sac_instance.seismogram.data)

        # try wrong type
        with pytest.raises(AttributeError):
            mini_clone = clone_to_mini(MiniStation, mini_seismogram)  # type: ignore

    def test_copy_from_mini(self, sac_instance: SAC) -> None:
        from pysmo.functions import copy_from_mini, clone_to_mini

        mini_station = clone_to_mini(MiniStation, sac_instance.station)
        assert mini_station.latitude == sac_instance.station.latitude
        mini_station.latitude /= 2
        assert mini_station.latitude != sac_instance.station.latitude
        copy_from_mini(mini_station, sac_instance.station)
        assert mini_station.latitude == sac_instance.station.latitude

        with pytest.raises(AttributeError):
            copy_from_mini(mini_station, sac_instance.seismogram)  # type: ignore
