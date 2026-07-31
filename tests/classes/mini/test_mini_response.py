import pytest

from pysmo import MiniResponse, Response


class TestMiniResponse:
    def test_create_instance(self) -> None:
        with pytest.raises(TypeError):
            MiniResponse()  # type: ignore

        response = MiniResponse(
            poles=[-0.037 + 0.037j, -0.037 - 0.037j],
            zeros=[0j, 0j],
            overall_sensitivity=3.4e9,
            input_units="M/S",
        )
        assert isinstance(response, MiniResponse)
        assert isinstance(response, Response)
        assert response.poles == [-0.037 + 0.037j, -0.037 - 0.037j]
        assert response.zeros == [0j, 0j]
        assert response.overall_sensitivity == 3.4e9
        assert response.input_units == "M/S"
        assert response.reference_sensitivity is None

    def test_converts_non_complex_values(self) -> None:
        response = MiniResponse(
            poles=[-1, -2],  # type: ignore[list-item]
            zeros=[0, 0],  # type: ignore[list-item]
            overall_sensitivity=1.0,
            input_units="M/S",
        )
        assert response.poles == [complex(-1), complex(-2)]
        assert all(isinstance(pole, complex) for pole in response.poles)

    def test_rejects_zero_sensitivity(self) -> None:
        with pytest.raises(ValueError):
            MiniResponse(poles=[], zeros=[], overall_sensitivity=0, input_units="M/S")

    def test_accepts_negative_sensitivity(self) -> None:
        """A negative overall_sensitivity is how a reversed-polarity channel
        is recorded (e.g. a negative SAC PZ CONSTANT/StationXML
        NormalizationFactor), not an error."""
        response = MiniResponse(
            poles=[], zeros=[], overall_sensitivity=-1, input_units="M/S"
        )
        assert response.overall_sensitivity == -1.0

    def test_change_attributes(self) -> None:
        response = MiniResponse(
            poles=[], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        response.overall_sensitivity = 2.0
        assert response.overall_sensitivity == 2.0
        response.overall_sensitivity = -1.0
        assert response.overall_sensitivity == -1.0
        with pytest.raises(ValueError):
            response.overall_sensitivity = 0.0

    def test_reference_sensitivity_optional_and_distinct_from_overall(self) -> None:
        """reference_sensitivity is independent of overall_sensitivity — the
        two carry different quantities (see Response.overall_sensitivity),
        so setting one must not affect the other."""
        response = MiniResponse(
            poles=[],
            zeros=[],
            overall_sensitivity=100.0,
            reference_sensitivity=4.0,
            input_units="M/S",
        )
        assert response.reference_sensitivity == 4.0
        assert response.overall_sensitivity == 100.0

    def test_rejects_zero_reference_sensitivity(self) -> None:
        with pytest.raises(ValueError):
            MiniResponse(
                poles=[],
                zeros=[],
                overall_sensitivity=1.0,
                reference_sensitivity=0,
                input_units="M/S",
            )

    def test_accepts_negative_reference_sensitivity(self) -> None:
        response = MiniResponse(
            poles=[],
            zeros=[],
            overall_sensitivity=1.0,
            reference_sensitivity=-4.0,
            input_units="M/S",
        )
        assert response.reference_sensitivity == -4.0
