"""Tests for pysmo.tools.signal.remove_response."""

from pathlib import Path

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
import scipy.signal
from syrupy.assertion import SnapshotAssertion

from pysmo import (
    MiniResponse,
    MiniResponseStage,
    MiniSeismogram,
    MiniStagedResponse,
    Seismogram,
)
from pysmo.classes import StationXML
from pysmo.tools.signal import remove_response
from tests.test_helpers import assert_seismogram_modification


def _analog_response(
    poles: list[complex], zeros: list[complex], sensitivity: float, freqs: np.ndarray
) -> np.ndarray:
    """Reference (test-only) analog transfer function, independent of the
    implementation under test."""
    s = 1j * 2 * np.pi * freqs
    h = np.full_like(s, sensitivity, dtype=complex)
    for zero in zeros:
        h *= s - zero
    for pole in poles:
        h /= s - pole
    return h


@pytest.fixture()
def dt() -> float:
    return 0.05


@pytest.fixture()
def npts() -> int:
    return 4096


@pytest.fixture()
def ground_motion(npts: int) -> np.ndarray:
    # Band-limited (DC and Nyquist bins zeroed): a real signal's DC/Nyquist
    # spectral bins must themselves be real, which a complex analog transfer
    # function evaluated at those exact frequencies generally violates. Zeroing
    # them avoids that (physically irrelevant, boundary-only) inconsistency so
    # the round-trip comparisons below aren't polluted by it.
    rng = np.random.default_rng(0)
    n_bins = npts // 2 + 1
    spectrum = rng.standard_normal(n_bins) + 1j * rng.standard_normal(n_bins)
    spectrum[0] = 0.0
    spectrum[-1] = 0.0
    return np.fft.irfft(spectrum, n=npts)


class TestRoundTrip:
    def test_analog_only_round_trip(
        self, dt: float, npts: int, ground_motion: np.ndarray
    ) -> None:
        poles = [-1.0 + 0j]
        zeros: list[complex] = []
        sensitivity = 5.0

        freqs = np.fft.rfftfreq(npts, d=dt)
        h = _analog_response(poles, zeros, sensitivity, freqs)
        counts = np.fft.irfft(np.fft.rfft(ground_motion) * h, n=npts)

        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=counts,
        )
        response = MiniResponse(
            poles=poles, zeros=zeros, overall_sensitivity=sensitivity, input_units="M/S"
        )
        # ground_motion has its DC and Nyquist bins zeroed (see fixture), so a
        # pre_filt whose taper only touches those two bins (ramps confined to
        # half a bin width either side) is a no-op everywhere the signal is
        # actually nonzero, letting the round trip stay exact.
        half_bin = freqs[1] / 2
        pre_filt = (half_bin / 2, half_bin, freqs[-1] - half_bin, freqs[-1])
        recovered = remove_response(seismogram, response, pre_filt=pre_filt, clone=True)

        npt.assert_allclose(recovered.data, ground_motion, rtol=1e-6, atol=1e-6)

    def test_digital_stage_round_trip_more_accurate_than_analog_only(
        self, dt: float, npts: int, ground_motion: np.ndarray
    ) -> None:
        poles = [-2.0 + 0j]
        zeros: list[complex] = []
        sensitivity = 3.0
        fs = 1 / dt
        nyquist = fs / 2

        fir = scipy.signal.firwin(31, 0.7 * nyquist, fs=fs)

        freqs = np.fft.rfftfreq(npts, d=dt)
        analog_h = _analog_response(poles, zeros, sensitivity, freqs)
        _, digital_h = scipy.signal.freqz(fir, [1.0], worN=freqs, fs=fs)
        full_h = analog_h * digital_h

        counts = np.fft.irfft(np.fft.rfft(ground_motion) * full_h, n=npts)
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=counts,
        )

        staged_response = MiniStagedResponse(
            poles=poles,
            zeros=zeros,
            overall_sensitivity=sensitivity,
            input_units="M/S",
            stages=[
                MiniResponseStage(
                    input_sample_rate=fs, decimation_factor=1, numerator=list(fir)
                )
            ],
        )
        analog_only_response = MiniResponse(
            poles=poles, zeros=zeros, overall_sensitivity=sensitivity, input_units="M/S"
        )

        half_bin = freqs[1] / 2
        pre_filt = (half_bin / 2, half_bin, freqs[-1] - half_bin, freqs[-1])

        recovered_staged = remove_response(
            MiniSeismogram(
                begin_time=seismogram.begin_time,
                delta=seismogram.delta,
                data=seismogram.data,
            ),
            staged_response,
            pre_filt=pre_filt,
            clone=True,
        )
        recovered_analog_only = remove_response(
            MiniSeismogram(
                begin_time=seismogram.begin_time,
                delta=seismogram.delta,
                data=seismogram.data,
            ),
            analog_only_response,
            pre_filt=pre_filt,
            clone=True,
        )

        # Content in the FIR stage's stopband is attenuated by the stage's
        # own transfer function, so it cannot be recovered exactly; what
        # matters here is that including the digital stage recovers
        # substantially more of the signal than the analog-only path does.
        error_staged = np.sqrt(np.mean((recovered_staged.data - ground_motion) ** 2))
        error_analog_only = np.sqrt(
            np.mean((recovered_analog_only.data - ground_motion) ** 2)
        )

        assert error_staged < 0.5 * error_analog_only


class TestDigitalStageCorrection:
    """`ResponseStage.correction` compensates for a decimation filter's own
    delay already being removed from the recorded data (FDSN StationXML's
    `Decimation/Correction`) -- see _digital_transfer_function."""

    def test_correction_rotates_phase_by_exp_two_pi_i_f_correction(self) -> None:
        from pysmo.tools.signal._response import _digital_transfer_function

        freqs = np.array([0.0, 1.0, 2.5, 5.0])
        correction = 0.5
        # A single-tap, unit-gain FIR stage has H(f) == 1+0j everywhere on
        # its own, so any deviation from that after correction is applied
        # is exactly the correction's own phase contribution.
        stage = MiniResponseStage(
            input_sample_rate=20.0,
            decimation_factor=1,
            numerator=[1.0],
            correction=correction,
        )
        response = MiniStagedResponse(
            poles=[],
            zeros=[],
            overall_sensitivity=1.0,
            input_units="M/S",
            stages=[stage],
        )

        h = _digital_transfer_function(response, freqs)

        npt.assert_allclose(h, np.exp(2j * np.pi * freqs * correction))

    def test_zero_correction_is_a_no_op(self) -> None:
        from pysmo.tools.signal._response import _digital_transfer_function

        freqs = np.array([0.0, 1.0, 2.5, 5.0])
        stage = MiniResponseStage(
            input_sample_rate=20.0, decimation_factor=1, numerator=[1.0]
        )
        response = MiniStagedResponse(
            poles=[],
            zeros=[],
            overall_sensitivity=1.0,
            input_units="M/S",
            stages=[stage],
        )

        h = _digital_transfer_function(response, freqs)

        npt.assert_allclose(h, np.ones_like(freqs, dtype=complex))

    def test_multi_stage_corrections_compose_across_cascade(self) -> None:
        """Correction composes across a decimation cascade as a simple sum
        of phases — each stage's `exp(2j*pi*f*correction)` multiplies in
        independently — and, being complex multiplication, must not depend
        on which position in the cascade a given stage occupies."""
        from pysmo.tools.signal._response import _digital_transfer_function

        freqs = np.array([0.0, 1.0, 2.5, 5.0])
        correction_1 = 0.5
        correction_2 = 1.3
        # Two unit-gain, single-tap stages (H(f) == 1+0j individually) so any
        # deviation after correction is purely each stage's own phase term.
        stage_1 = MiniResponseStage(
            input_sample_rate=20.0,
            decimation_factor=1,
            numerator=[1.0],
            correction=correction_1,
        )
        stage_2 = MiniResponseStage(
            input_sample_rate=20.0,
            decimation_factor=1,
            numerator=[1.0],
            correction=correction_2,
        )
        expected = np.exp(2j * np.pi * freqs * (correction_1 + correction_2))

        forward = MiniStagedResponse(
            poles=[],
            zeros=[],
            overall_sensitivity=1.0,
            input_units="M/S",
            stages=[stage_1, stage_2],
        )
        npt.assert_allclose(_digital_transfer_function(forward, freqs), expected)

        reversed_order = MiniStagedResponse(
            poles=[],
            zeros=[],
            overall_sensitivity=1.0,
            input_units="M/S",
            stages=[stage_2, stage_1],
        )
        npt.assert_allclose(_digital_transfer_function(reversed_order, freqs), expected)

    def test_correction_recovers_shape_lost_to_uncorrected_stage_delay(
        self, dt: float, npts: int, ground_motion: np.ndarray
    ) -> None:
        """An asymmetric FIR stage's raw coefficients carry the stage's own
        group delay; a real digitiser already removes that delay from the
        recorded data. Simulating that -- applying the raw filter, then
        shifting the result back by its own delay, exactly as a real
        digitiser would -- should only round-trip through remove_response
        when `correction` matches, not when it is left at 0."""
        fs = 1 / dt
        # An asymmetric FIR with a clear, known group delay: a single tap
        # offset from the start, i.e. a pure n-sample delay filter.
        delay_samples = 4
        numerator = [0.0] * delay_samples + [1.0]
        correction = delay_samples * dt

        freqs = np.fft.rfftfreq(npts, d=dt)
        _, raw_h = scipy.signal.freqz(numerator, [1.0], worN=freqs, fs=fs)
        filtered = np.fft.irfft(np.fft.rfft(ground_motion) * raw_h, n=npts)
        # A real digitiser timestamps its output as if this stage had no
        # delay, by shifting the data earlier by `correction` seconds.
        recorded = np.roll(filtered, -delay_samples)

        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=recorded,
        )
        half_bin = freqs[1] / 2
        pre_filt = (half_bin / 2, half_bin, freqs[-1] - half_bin, freqs[-1])

        def _recovered(correction_value: float) -> np.ndarray:
            response = MiniStagedResponse(
                poles=[],
                zeros=[],
                overall_sensitivity=1.0,
                input_units="M/S",
                stages=[
                    MiniResponseStage(
                        input_sample_rate=fs,
                        decimation_factor=1,
                        numerator=numerator,
                        correction=correction_value,
                    )
                ],
            )
            return remove_response(
                seismogram, response, pre_filt=pre_filt, clone=True
            ).data

        error_with_correction = np.sqrt(
            np.mean((_recovered(correction) - ground_motion) ** 2)
        )
        error_without_correction = np.sqrt(
            np.mean((_recovered(0.0) - ground_motion) ** 2)
        )

        npt.assert_allclose(error_with_correction, 0.0, atol=1e-6)
        assert error_without_correction > 0.5 * np.sqrt(np.mean(ground_motion**2))


class TestEmptyStages:
    def test_empty_stages_matches_plain_response(
        self, dt: float, npts: int, ground_motion: np.ndarray
    ) -> None:
        poles = [-1.0 + 0j]
        zeros: list[complex] = []
        sensitivity = 5.0

        freqs = np.fft.rfftfreq(npts, d=dt)
        h = _analog_response(poles, zeros, sensitivity, freqs)
        counts = np.fft.irfft(np.fft.rfft(ground_motion) * h, n=npts)

        response = MiniResponse(
            poles=poles, zeros=zeros, overall_sensitivity=sensitivity, input_units="M/S"
        )
        staged_response = MiniStagedResponse(
            poles=poles,
            zeros=zeros,
            overall_sensitivity=sensitivity,
            input_units="M/S",
            stages=[],
        )

        seismogram1 = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=counts.copy(),
        )
        seismogram2 = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=counts.copy(),
        )

        half_bin = freqs[1] / 2
        pre_filt = (half_bin / 2, half_bin, freqs[-1] - half_bin, freqs[-1])

        result_plain = remove_response(
            seismogram1, response, pre_filt=pre_filt, clone=True
        )
        result_staged = remove_response(
            seismogram2, staged_response, pre_filt=pre_filt, clone=True
        )

        npt.assert_array_equal(result_plain.data, result_staged.data)


class TestSensitivityOnly:
    """The sensitivity-only, no-`pre_filt` path: plain scalar division, no FFT."""

    def test_divides_by_reference_sensitivity(
        self, dt: float, ground_motion: np.ndarray
    ) -> None:
        """Must divide by reference_sensitivity, not overall_sensitivity: the
        latter has the response's A0 normalisation factor folded in (see
        Response.overall_sensitivity), so using it directly would mis-scale
        the result. overall_sensitivity is deliberately set to a different
        value here so a regression back to dividing by it is caught."""
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j, -2.0 + 0j],
            zeros=[0j],
            overall_sensitivity=100.0,
            reference_sensitivity=4.0,
            input_units="M/S",
        )
        removed = remove_response(seismogram, response, clone=True)
        npt.assert_array_equal(removed.data, ground_motion / 4.0)

    def test_ignores_digital_stages(self, dt: float, ground_motion: np.ndarray) -> None:
        """Only reference_sensitivity matters; stage filter shape is
        irrelevant without a pre_filt-triggered spectral deconvolution."""
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniStagedResponse(
            poles=[-1.0 + 0j],
            zeros=[],
            overall_sensitivity=4.0,
            reference_sensitivity=4.0,
            input_units="M/S",
            stages=[
                MiniResponseStage(
                    input_sample_rate=1 / dt, decimation_factor=1, numerator=[0.5, 0.5]
                )
            ],
        )
        removed = remove_response(seismogram, response, clone=True)
        npt.assert_array_equal(removed.data, ground_motion / 4.0)

    def test_missing_reference_sensitivity_raises(
        self, dt: float, ground_motion: np.ndarray
    ) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        assert response.reference_sensitivity is None
        with pytest.raises(ValueError, match="reference_sensitivity"):
            remove_response(seismogram, response)


class TestZeroHandling:
    def test_zero_excluded_by_taper_does_not_produce_inf_or_nan(
        self, dt: float, npts: int, ground_motion: np.ndarray
    ) -> None:
        """A response zero at DC combined with a pre_filt that excludes DC
        (taper == 0 there) must not turn 0/0 into nan and poison the whole
        output."""
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j],
            zeros=[0j],
            overall_sensitivity=1.0,
            input_units="M/S",
        )
        removed = remove_response(
            seismogram,
            response,
            pre_filt=(1e-6, 1e-5, 0.8 * nyquist, 0.9 * nyquist),
            clone=True,
        )
        assert np.all(np.isfinite(removed.data))

    def test_zero_inside_passband_produces_non_finite_output(
        self, dt: float, npts: int, ground_motion: np.ndarray
    ) -> None:
        """No stabilisation is applied inside the chosen passband: a
        response zero that falls squarely within the flat [f2, f3] region
        divides by exactly zero there, and is expected to blow up, since it
        is the caller's responsibility to choose corners that avoid the
        response's own poles/zeros."""
        freqs = np.fft.rfftfreq(npts, d=dt)
        f0 = freqs[50]
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j],
            zeros=[1j * 2 * np.pi * f0],
            overall_sensitivity=1.0,
            input_units="M/S",
        )
        removed = remove_response(
            seismogram,
            response,
            pre_filt=(freqs[1] / 2, freqs[10], freqs[-10], freqs[-1] - freqs[1] / 2),
            clone=True,
        )
        assert not np.all(np.isfinite(removed.data))


class TestPreFiltValidation:
    @pytest.mark.parametrize(
        "pre_filt",
        [
            (2.0, 1.0, 3.0, 4.0),
            (1.0, 3.0, 2.0, 4.0),
            (1.0, 2.0, 4.0, 3.0),
            (1.0, 1.0, 2.0, 3.0),
        ],
    )
    def test_non_increasing_corners_raise(
        self,
        dt: float,
        ground_motion: np.ndarray,
        pre_filt: tuple[float, float, float, float],
    ) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        with pytest.raises(ValueError, match="pre_filt"):
            remove_response(seismogram, response, pre_filt=pre_filt)

    def test_upper_corner_above_nyquist_raises(
        self, dt: float, ground_motion: np.ndarray
    ) -> None:
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        with pytest.raises(ValueError, match="Nyquist"):
            remove_response(
                seismogram,
                response,
                pre_filt=(0.1, 1.0, 2.0, nyquist + 1.0),
            )

    def test_equal_f2_f3_allowed(self, dt: float, ground_motion: np.ndarray) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        remove_response(seismogram, response, pre_filt=(0.1, 2.0, 2.0, 5.0))


class TestEmptySeismogram:
    def test_raises(self, dt: float) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=np.array([]),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        with pytest.raises(ValueError, match="empty"):
            remove_response(seismogram, response)


class TestNearNyquistWarning:
    def test_plain_response_warns_near_nyquist(self, ground_motion: np.ndarray) -> None:
        dt = 0.01
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        with pytest.warns(UserWarning, match="digital stages"):
            remove_response(
                seismogram,
                response,
                pre_filt=(0.01, 0.05, 0.9 * nyquist, 0.95 * nyquist),
            )

    def test_empty_stages_warns_near_nyquist(self, ground_motion: np.ndarray) -> None:
        """A `StagedResponse` with an empty `stages` list carries no more
        real digital-stage information than a plain `Response` -- it must
        still warn, even though it satisfies `StagedResponse` structurally."""
        dt = 0.01
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniStagedResponse(
            poles=[-1.0 + 0j],
            zeros=[],
            overall_sensitivity=1.0,
            input_units="M/S",
            stages=[],
        )
        with pytest.warns(UserWarning, match="digital stages"):
            remove_response(
                seismogram,
                response,
                pre_filt=(0.01, 0.05, 0.9 * nyquist, 0.95 * nyquist),
            )

    def test_populated_stages_does_not_warn_when_f4_within_stage_nyquist(
        self, ground_motion: np.ndarray, recwarn: pytest.WarningsRecorder
    ) -> None:
        """A stage whose own Nyquist comfortably covers `f4` should not warn,
        even though `f4` is close to the seismogram's own Nyquist."""
        dt = 0.01
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniStagedResponse(
            poles=[-1.0 + 0j],
            zeros=[],
            overall_sensitivity=1.0,
            input_units="M/S",
            stages=[
                MiniResponseStage(
                    input_sample_rate=10 / dt, decimation_factor=1, numerator=[1.0]
                )
            ],
        )
        remove_response(
            seismogram,
            response,
            pre_filt=(0.01, 0.05, 0.9 * nyquist, 0.95 * nyquist),
        )
        assert len(recwarn) == 0

    def test_populated_stages_warns_when_f4_exceeds_stage_nyquist(
        self, ground_motion: np.ndarray
    ) -> None:
        """A stage's own Nyquist can be tighter than the seismogram's; `f4`
        pushed past it should warn even though `stages` is populated -- this
        is the case `scipy.signal.freqz`'s periodicity silently aliases."""
        dt = 0.01
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniStagedResponse(
            poles=[-1.0 + 0j],
            zeros=[],
            overall_sensitivity=1.0,
            input_units="M/S",
            stages=[
                MiniResponseStage(
                    input_sample_rate=1 / dt, decimation_factor=1, numerator=[1.0]
                )
            ],
        )
        with pytest.warns(UserWarning, match="stages' own Nyquist"):
            remove_response(
                seismogram,
                response,
                pre_filt=(0.01, 0.05, 0.9 * nyquist, 0.95 * nyquist),
            )

    def test_no_warning_when_pre_filt_is_none(
        self, ground_motion: np.ndarray, recwarn: pytest.WarningsRecorder
    ) -> None:
        dt = 0.01
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j],
            zeros=[],
            overall_sensitivity=1.0,
            reference_sensitivity=1.0,
            input_units="M/S",
        )
        remove_response(seismogram, response)
        assert len(recwarn) == 0

    def test_no_warning_when_corner_below_threshold(
        self, ground_motion: np.ndarray, recwarn: pytest.WarningsRecorder
    ) -> None:
        dt = 0.01
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        remove_response(
            seismogram, response, pre_filt=(0.01, 0.05, 0.5 * nyquist, 0.6 * nyquist)
        )
        assert len(recwarn) == 0


class TestSnapshot:
    def test_full_pipeline_matches_snapshot(
        self,
        seismogram: Seismogram,
        snapshot: SnapshotAssertion,
        reference_event_assets: dict[str, Path],
    ) -> None:
        """Regression guard alongside the round-trip correctness tests above:
        a snapshot can't catch a systematically wrong transfer function, but
        it does catch accidental behaviour changes in the full pipeline."""
        response = StationXML.from_bytes(
            reference_event_assets["stationxml_bhz"].read_bytes(),
            time=seismogram.begin_time,
        ).response
        nyquist = 0.5 / seismogram.delta.total_seconds()
        f4 = 0.8 * nyquist
        f3 = f4 * 0.9
        f1 = min(abs(pole) for pole in response.poles if pole != 0) / 10
        f2 = f1 * 10
        assert_seismogram_modification(
            seismogram,
            remove_response,
            response,
            pre_filt=(f1, f2, f3, f4),
            expected_data=snapshot,
            # Deconvolved ground motion is physically tiny (order 1e-4 m/s
            # or smaller) — the default 6 decimals would round away almost
            # all of it.
            snapshot_decimals=10,
        )


class TestClone:
    def test_clone_matches_in_place(self, dt: float, ground_motion: np.ndarray) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j],
            zeros=[],
            overall_sensitivity=1.0,
            reference_sensitivity=1.0,
            input_units="M/S",
        )
        assert_seismogram_modification(seismogram, remove_response, response)

    def test_clone_matches_in_place_with_pre_filt(
        self, dt: float, ground_motion: np.ndarray
    ) -> None:
        nyquist = 0.5 / dt
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=ground_motion.copy(),
        )
        response = MiniResponse(
            poles=[-1.0 + 0j], zeros=[], overall_sensitivity=1.0, input_units="M/S"
        )
        assert_seismogram_modification(
            seismogram,
            remove_response,
            response,
            pre_filt=(1e-6, 1e-5, 0.8 * nyquist, 0.9 * nyquist),
        )
