"""Tests for pysmo.tools.signal.integrate/differentiate."""

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from pysmo import MiniSeismogram
from pysmo.tools.signal import differentiate, integrate
from tests.test_helpers import assert_seismogram_modification


@pytest.fixture()
def dt() -> float:
    return 0.1


@pytest.fixture()
def sine_seismogram(dt: float) -> MiniSeismogram:
    npts = 250  # exact number of cycles of the 1 Hz signal below
    t = np.arange(npts) * dt
    omega = 2 * np.pi * 1.0
    return MiniSeismogram(
        begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
        delta=pd.Timedelta(seconds=dt),
        data=np.sin(omega * t),
    )


class TestDifferentiate:
    def test_matches_analytical_derivative(
        self, dt: float, sine_seismogram: MiniSeismogram
    ) -> None:
        npts = len(sine_seismogram.data)
        t = np.arange(npts) * dt
        omega = 2 * np.pi * 1.0
        expected = omega * np.cos(omega * t)

        result = differentiate(sine_seismogram, clone=True)
        npt.assert_allclose(result.data, expected, atol=1e-6)

    def test_constant_offset_differentiates_to_zero(self, dt: float) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=np.full(64, 3.0),
        )
        result = differentiate(seismogram, clone=True)
        npt.assert_allclose(result.data, 0.0, atol=1e-9)

    def test_clone_matches_in_place(self, sine_seismogram: MiniSeismogram) -> None:
        assert_seismogram_modification(sine_seismogram, differentiate)

    def test_empty_seismogram_raises(self, dt: float) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=np.array([]),
        )
        with pytest.raises(ValueError, match="empty"):
            differentiate(seismogram)


class TestIntegrate:
    def test_matches_analytical_integral(
        self, dt: float, sine_seismogram: MiniSeismogram
    ) -> None:
        npts = len(sine_seismogram.data)
        t = np.arange(npts) * dt
        omega = 2 * np.pi * 1.0
        cosine_seismogram = MiniSeismogram(
            begin_time=sine_seismogram.begin_time,
            delta=sine_seismogram.delta,
            data=omega * np.cos(omega * t),
        )
        expected = np.sin(omega * t)

        result = integrate(cosine_seismogram, clone=True)
        npt.assert_allclose(result.data, expected, atol=1e-6)

    def test_round_trip_with_differentiate(
        self, sine_seismogram: MiniSeismogram
    ) -> None:
        differentiated = differentiate(sine_seismogram, clone=True)
        recovered = integrate(differentiated, clone=True)
        npt.assert_allclose(recovered.data, sine_seismogram.data, atol=1e-6)

    def test_dc_bin_forced_to_zero_not_inf_or_nan(self, dt: float) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=np.full(64, 3.0),
        )
        result = integrate(seismogram, clone=True)
        assert np.all(np.isfinite(result.data))

    def test_clone_matches_in_place(self, sine_seismogram: MiniSeismogram) -> None:
        assert_seismogram_modification(sine_seismogram, integrate)

    def test_empty_seismogram_raises(self, dt: float) -> None:
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-01-01T00:00:00Z"),
            delta=pd.Timedelta(seconds=dt),
            data=np.array([]),
        )
        with pytest.raises(ValueError, match="empty"):
            integrate(seismogram)
