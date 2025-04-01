from pysmo import LocationWithDepth, MiniLocationWithDepth
import pytest


class TestMiniLocationWithDepth:
    def test_create_instance(self) -> None:
        """Test creating an instance."""

        with pytest.raises(TypeError):
            minihypocenter = MiniLocationWithDepth()  # type: ignore
        latitude, longitude, depth = 1.1, 2.2, 1000
        minihypocenter = MiniLocationWithDepth(
            latitude=latitude, longitude=longitude, depth=depth
        )
        assert isinstance(minihypocenter, MiniLocationWithDepth)
        assert isinstance(minihypocenter, LocationWithDepth)

    @pytest.mark.depends(name="test_create_instance")
    def test_change_attributes(self) -> None:
        latitude, longitude, depth = 1.1, 2.2, 1000
        new_latitude, new_longitude, new_depth = -21.1, -22.2, 500.2

        minihypocenter = MiniLocationWithDepth(
            latitude=latitude, longitude=longitude, depth=depth
        )

        assert isinstance(minihypocenter, LocationWithDepth)

        assert minihypocenter.depth == depth
        assert minihypocenter.latitude == latitude
        assert minihypocenter.longitude == longitude

        minihypocenter.depth = new_depth
        assert minihypocenter.depth == new_depth
        minihypocenter.latitude = new_latitude
        assert minihypocenter.latitude == new_latitude
        minihypocenter.longitude = new_longitude
        assert minihypocenter.longitude == new_longitude

        with pytest.raises(ValueError):
            minihypocenter.latitude = -100
        with pytest.raises(ValueError):
            minihypocenter.latitude = 100
        with pytest.raises(ValueError):
            minihypocenter.longitude = -180
        with pytest.raises(ValueError):
            minihypocenter.latitude = 181
