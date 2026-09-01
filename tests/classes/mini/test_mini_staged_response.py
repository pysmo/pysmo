import pytest

from pysmo import MiniResponseStage, MiniStagedResponse


class TestMiniResponseStage:
    def test_create_instance(self) -> None:
        with pytest.raises(TypeError):
            MiniResponseStage()  # type: ignore

        stage = MiniResponseStage(
            input_sample_rate=40.0, decimation_factor=1, numerator=[0.5, 0.5]
        )
        assert isinstance(stage, MiniResponseStage)
        assert stage.input_sample_rate == 40.0
        assert stage.decimation_factor == 1
        assert stage.numerator == [0.5, 0.5]
        assert stage.denominator == [1.0]
        assert stage.correction == 0.0

    def test_rejects_non_positive_input_sample_rate(self) -> None:
        with pytest.raises(ValueError):
            MiniResponseStage(input_sample_rate=0, decimation_factor=1, numerator=[1.0])
        with pytest.raises(ValueError):
            MiniResponseStage(
                input_sample_rate=-1, decimation_factor=1, numerator=[1.0]
            )

    def test_rejects_non_positive_decimation_factor(self) -> None:
        with pytest.raises(ValueError):
            MiniResponseStage(
                input_sample_rate=40.0, decimation_factor=0, numerator=[1.0]
            )
        with pytest.raises(ValueError):
            MiniResponseStage(
                input_sample_rate=40.0, decimation_factor=-1, numerator=[1.0]
            )

    def test_explicit_denominator(self) -> None:
        stage = MiniResponseStage(
            input_sample_rate=40.0,
            decimation_factor=1,
            numerator=[1.0],
            denominator=[1.0, -0.5],
        )
        assert stage.denominator == [1.0, -0.5]

    def test_explicit_correction(self) -> None:
        stage = MiniResponseStage(
            input_sample_rate=40.0,
            decimation_factor=1,
            numerator=[1.0],
            correction=0.82,
        )
        assert stage.correction == pytest.approx(0.82)


class TestMiniStagedResponse:
    def test_create_instance(self) -> None:
        response = MiniStagedResponse(
            poles=[-0.037 + 0.037j],
            zeros=[0j],
            overall_sensitivity=3.4e9,
            input_units="M/S",
            stages=[
                MiniResponseStage(
                    input_sample_rate=40.0, decimation_factor=1, numerator=[1.0]
                )
            ],
        )
        assert isinstance(response, MiniStagedResponse)
        assert len(response.stages) == 1

    def test_empty_stages_still_satisfies_staged_response(self) -> None:
        response = MiniStagedResponse(
            poles=[], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        assert response.stages == []

    def test_reference_sensitivity_inherited_from_mini_response(self) -> None:
        response = MiniStagedResponse(
            poles=[],
            zeros=[],
            overall_sensitivity=100.0,
            reference_sensitivity=4.0,
            input_units="M/S",
        )
        assert response.reference_sensitivity == 4.0
