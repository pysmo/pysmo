import pytest
from pysmo import MiniLocation, Location


class TestMiniLocation:

    def test_create_instance(self) -> None:
        """Test creating an instance."""

        # can't create an instnce without kwargs
        with pytest.raises(TypeError):
            minilocation = MiniLocation()  # type: ignore

        latitude, longitude = 1.1, 2.2
        minilocation = MiniLocation(latitude=latitude, longitude=longitude)
        assert isinstance(minilocation, MiniLocation)
        assert isinstance(minilocation, Location)
        assert minilocation.latitude == 1.1
        assert minilocation.longitude == 2.2

    @pytest.mark.depends(name='test_create_instance')
    def test_change_attributes(self) -> None:
        """Test changing attributes."""

        latitude, longitude = 1.1, 2.2
        minilocation = MiniLocation(latitude=latitude, longitude=longitude)
        minilocation.latitude = -90
        minilocation.latitude = 90
        assert minilocation.latitude == 90
        with pytest.raises(ValueError):
            minilocation.latitude = -91
        with pytest.raises(ValueError):
            minilocation.latitude = 91
        minilocation.longitude = -179.9
        minilocation.longitude = 180
        assert minilocation.longitude == 180
        with pytest.raises(ValueError):
            minilocation.longitude = -180
        with pytest.raises(ValueError):
            minilocation.longitude = 181
