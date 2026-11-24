import pytest
from hypothesis import given
from hypothesis import strategies as st

from pysmo import MiniOrientation
from pysmo.lib.converters import to_azimuth

_finite = st.floats(allow_nan=False, allow_infinity=False)
_dips = st.floats(min_value=-90, max_value=90)
_bad_dips = st.floats(min_value=90, exclude_min=True) | st.floats(
    max_value=-90, exclude_max=True
)


class TestMiniOrientation:
    def test_create_instance(self) -> None:
        with pytest.raises(TypeError):
            MiniOrientation()  # type: ignore[call-arg]

        orientation = MiniOrientation(azimuth=45, dip=-90)
        assert orientation.azimuth == 45
        assert orientation.dip == -90
        assert isinstance(orientation.azimuth, float)
        assert isinstance(orientation.dip, float)

    @given(_finite)
    def test_azimuth_is_wrapped(self, value: float) -> None:
        orientation = MiniOrientation(azimuth=value, dip=0)
        assert orientation.azimuth == to_azimuth(value)
        orientation.azimuth = value
        assert orientation.azimuth == to_azimuth(value)

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), "abc"])
    def test_azimuth_rejects_non_finite(self, value: float) -> None:
        with pytest.raises(ValueError):
            MiniOrientation(azimuth=value, dip=0)

    @given(_dips)
    def test_dip_in_range_is_kept(self, value: float) -> None:
        orientation = MiniOrientation(azimuth=0, dip=value)
        assert orientation.dip == value
        orientation.dip = value
        assert orientation.dip == value

    @given(_bad_dips | st.just(float("nan")))
    def test_dip_out_of_range_is_rejected(self, value: float) -> None:
        with pytest.raises(ValueError):
            MiniOrientation(azimuth=0, dip=value)
        orientation = MiniOrientation(azimuth=0, dip=0)
        with pytest.raises(ValueError):
            orientation.dip = value
