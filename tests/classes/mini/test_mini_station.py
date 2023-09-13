import pytest
from pysmo import Station, MiniStation


class TestMiniStation:
    def test_create_instance(self) -> None:
        """Test creating an instance."""

        # can't create an instance without kwargs
        with pytest.raises(TypeError):
            ministation = MiniStation()  # type: ignore

        name, latitude, longitude = "station", 1.1, 2.2
        ministation = MiniStation(name=name, latitude=latitude, longitude=longitude)
        assert isinstance(ministation, MiniStation)
        assert isinstance(ministation, Station)
        assert ministation.name == "station"
        assert ministation.latitude == 1.1
        assert ministation.longitude == 2.2

    @pytest.mark.depends(name="test_create_instance")
    def test_change_attributes(self) -> None:
        """Test changing attributes."""

        name, latitude, longitude = "station", 1.1, 2.2
        ministation = MiniStation(name=name, latitude=latitude, longitude=longitude)
        ministation.network = "newnetwork"
        assert ministation.network == "newnetwork"
        with pytest.raises(ValueError):
            ministation.elevation = "abc"  # type: ignore
        ministation.elevation = 123
        assert ministation.elevation == 123
        ministation.name = "newname"
        assert ministation.name == "newname"
        ministation.latitude = -90
        ministation.latitude = 90
        assert ministation.latitude == 90
        with pytest.raises(ValueError):
            ministation.latitude = -91
        with pytest.raises(ValueError):
            ministation.latitude = 91
        ministation.longitude = -179.9
        ministation.longitude = 180
        assert ministation.longitude == 180
        with pytest.raises(ValueError):
            ministation.longitude = -180
        with pytest.raises(ValueError):
            ministation.longitude = 181
