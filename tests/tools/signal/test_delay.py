from pysmo.tools.signal import delay, multi_delay, multi_multi_delay, mccc
from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import detrend, clone_to_mini
from pytest_cases import parametrize_with_cases
import pytest
import numpy as np
from pandas import Timedelta
import random


def test_delay_basic() -> None:
    data1 = np.array([1, 1, 1, 1, 2, 3, 4, 1, 1])
    data2 = np.array([1, 1, 1, 2, 3, 4, 1])
    seismogram1 = MiniSeismogram(data=data1)
    seismogram2 = MiniSeismogram(data=data2)
    cc_delay, cc_coeff = delay(seismogram1, seismogram2)
    assert cc_delay.total_seconds() == pytest.approx(-1)
    assert cc_coeff == pytest.approx(1)


def test_delay_with_total_delay_true() -> None:
    data1 = np.array([1, 1, 1, 1, 2, 3, 4, 1, 1])
    data2 = np.array([1, 1, 1, 2, 3, 4, 1])
    seismogram1 = MiniSeismogram(data=data1)
    seismogram2 = MiniSeismogram(data=data2)
    seismogram2.begin_time += Timedelta(seconds=1)
    cc_delay, cc_coeff = delay(seismogram1, seismogram2, total_delay=True)
    assert cc_delay.total_seconds() == pytest.approx(-2)
    assert cc_coeff == pytest.approx(1)


def test_delay_with_allow_negative_true() -> None:
    data1 = np.array([1, 1, 1, 1, 2, 3, 4, 1, 1])
    data2 = np.array([1, 1, 1, 2, 3, 4, 1])
    seismogram1 = MiniSeismogram(data=data1)
    seismogram2 = MiniSeismogram(data=-data2)
    detrend(seismogram2)
    cc_delay, cc_coeff = delay(seismogram1, seismogram2, abs_max=True)
    assert cc_delay.total_seconds() == pytest.approx(-1)
    assert cc_coeff < 0


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_delay_with_seismogram(seismogram: Seismogram) -> None:
    rand_int = int(random.uniform(10, 100))
    seismogram1 = clone_to_mini(MiniSeismogram, seismogram)
    seismogram1.data = seismogram.data[1000:10000]
    seismogram1 = detrend(seismogram1, clone=True)

    seismogram2 = clone_to_mini(MiniSeismogram, seismogram1)
    seismogram2.delta = seismogram1.delta * 2
    with pytest.raises(ValueError):
        cc_delay, _ = delay(seismogram1, seismogram2)

    seismogram2 = clone_to_mini(MiniSeismogram, seismogram1)
    seismogram2.data = seismogram1.data[0:rand_int]
    with pytest.raises(ValueError):
        cc_delay, _ = delay(seismogram1, seismogram2, max_shift=Timedelta(seconds=1))

    # create seismogram2 by cutting off first rand_int samples
    seismogram2 = clone_to_mini(MiniSeismogram, seismogram1)
    seismogram2.data = seismogram1.data[rand_int:]
    cc_delay, _ = delay(seismogram1, seismogram2)
    assert cc_delay == -rand_int * seismogram1.delta
    cc_delay, _ = delay(seismogram2, seismogram1)
    assert cc_delay == rand_int * seismogram1.delta

    # create seismogram2 by cutting off first rand_int samples and flipping polarity
    seismogram2 = clone_to_mini(MiniSeismogram, seismogram1)
    seismogram2.data = -seismogram1.data[rand_int:]
    cc_delay, _ = delay(seismogram1, seismogram2, abs_max=True)
    assert cc_delay == -rand_int * seismogram1.delta
    cc_delay, _ = delay(seismogram2, seismogram1, abs_max=True)
    assert cc_delay == rand_int * seismogram1.delta

    # create seismogram2 with a delay of rand_int * delta
    seismogram2 = clone_to_mini(MiniSeismogram, seismogram1)
    seismogram2.data = np.roll(seismogram1.data, rand_int)

    cc_delay, _ = delay(
        seismogram1,
        seismogram2,
        max_shift=rand_int * seismogram1.delta + Timedelta(seconds=2),
    )

    assert cc_delay == rand_int * seismogram1.delta

    cc_delay, _ = delay(
        seismogram2,
        seismogram1,
        max_shift=rand_int * seismogram1.delta + Timedelta(seconds=2),
    )

    assert cc_delay == -rand_int * seismogram1.delta


# --- multi_delay tests ---


def test_multi_delay_empty_list() -> None:
    """multi_delay returns empty arrays for an empty seismogram list."""
    template = MiniSeismogram(data=np.array([1.0, 2.0, 3.0, 2.0, 1.0]))
    delays, coeffs = multi_delay(template, [])
    assert len(delays) == 0
    assert len(coeffs) == 0


def test_multi_delay_single_identical() -> None:
    """Identical seismogram should have zero delay and high correlation."""
    data = np.sin(np.linspace(0, 4 * np.pi, 500))
    template = MiniSeismogram(data=data.copy())
    seis = MiniSeismogram(data=data.copy())
    delays, coeffs = multi_delay(template, [seis])
    assert delays[0].total_seconds() == pytest.approx(0, abs=1e-6)
    assert coeffs[0] == pytest.approx(1, abs=0.05)


def test_multi_delay_known_shift() -> None:
    """Shifted seismogram should yield a delay matching the known shift."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    nroll = 10
    seis = MiniSeismogram(data=np.roll(data, nroll))
    delays, coeffs = multi_delay(template, [seis])
    expected_delay = nroll * template.delta
    assert delays[0] == expected_delay
    assert coeffs[0] == pytest.approx(1, abs=0.05)


def test_multi_delay_multiple_seismograms() -> None:
    """Multiple seismograms with different shifts should each return the correct delay."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    shifts = [0, 5, -8, 15]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    delays, coeffs = multi_delay(template, seismograms)

    assert len(delays) == len(shifts)
    assert len(coeffs) == len(shifts)
    for i, shift in enumerate(shifts):
        expected_delay = shift * template.delta
        assert delays[i] == expected_delay
        assert coeffs[i] == pytest.approx(1, abs=0.05)


def test_multi_delay_abs_max() -> None:
    """With abs_max=True, a polarity-flipped seismogram should still yield the correct delay."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    nroll = 12
    seis = MiniSeismogram(data=-np.roll(data, nroll))
    delays, coeffs = multi_delay(template, [seis], abs_max=True)
    expected_delay = nroll * template.delta
    assert delays[0] == expected_delay
    assert coeffs[0] < 0


def test_multi_delay_different_delta_raises() -> None:
    """Seismograms with different sampling intervals should raise ValueError."""
    template = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis.delta = template.delta * 2
    with pytest.raises(ValueError):
        multi_delay(template, [seis])


def test_multi_delay_different_lengths() -> None:
    """Seismograms of different lengths should still produce correct delays."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    seis_short = MiniSeismogram(data=data[:800].copy())
    seis_long = MiniSeismogram(data=data.copy())

    delays, coeffs = multi_delay(template, [seis_short, seis_long])

    assert len(delays) == 2
    assert len(coeffs) == 2
    # The identical-length copy should have zero delay
    assert delays[1].total_seconds() == pytest.approx(0, abs=1e-6)
    assert coeffs[1] == pytest.approx(1, abs=0.05)


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_multi_delay_with_seismogram(seismogram: Seismogram) -> None:
    """Test multi_delay with real seismogram data and known shifts."""
    template = clone_to_mini(MiniSeismogram, seismogram)
    template.data = seismogram.data[1000:10000]
    template = detrend(template, clone=True)

    shifts = [0, 15, -20]
    seismograms = []
    for shift in shifts:
        seis = clone_to_mini(MiniSeismogram, template)
        seis.data = np.roll(template.data, shift)
        seismograms.append(seis)

    delays, coeffs = multi_delay(template, seismograms)

    for i, shift in enumerate(shifts):
        expected_delay = shift * template.delta
        assert delays[i] == expected_delay
        assert coeffs[i] == pytest.approx(1, abs=0.05)


# --- multi_multi_delay tests ---


def test_multi_multi_delay_empty_list() -> None:
    """Empty list returns empty (0, 0) arrays."""
    delays, coeffs = multi_multi_delay([])
    assert delays.shape == (0, 0)
    assert coeffs.shape == (0, 0)


def test_multi_multi_delay_single_seismogram() -> None:
    """Single seismogram returns (1, 1) empty arrays (no pairs to compare)."""
    seis = MiniSeismogram(data=np.sin(np.linspace(0, 4 * np.pi, 500)))
    delays, coeffs = multi_multi_delay([seis])
    assert delays.shape == (1, 1)
    assert coeffs.shape == (1, 1)


def test_multi_multi_delay_diagonal_zero() -> None:
    """Diagonal entries should have zero delay and high self-correlation."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    seismograms = [
        MiniSeismogram(data=data.copy()),
        MiniSeismogram(data=np.roll(data, 10)),
    ]
    delays, coeffs = multi_multi_delay(seismograms)
    for i in range(len(seismograms)):
        assert delays[i, i].total_seconds() == pytest.approx(0, abs=1e-6)
        assert coeffs[i, i] == pytest.approx(1, abs=0.05)


def test_multi_multi_delay_known_shifts() -> None:
    """All pairwise delays should match known shifts."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 5, -10]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    delays, coeffs = multi_multi_delay(seismograms)

    n = len(shifts)
    assert delays.shape == (n, n)
    assert coeffs.shape == (n, n)
    delta = seismograms[0].delta
    for i in range(n):
        for j in range(n):
            expected_delay = (shifts[j] - shifts[i]) * delta
            assert delays[i, j] == expected_delay
            assert coeffs[i, j] == pytest.approx(1, abs=0.05)


def test_multi_multi_delay_antisymmetric() -> None:
    """delays[i, j] should equal -delays[j, i]."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 7, -4, 15]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    delays, _ = multi_multi_delay(seismograms)

    n = len(shifts)
    for i in range(n):
        for j in range(n):
            assert delays[i, j] == -delays[j, i]


def test_multi_multi_delay_abs_max() -> None:
    """With abs_max=True, a polarity-flipped seismogram should still yield the correct delay."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    nroll = 12
    seismograms = [
        MiniSeismogram(data=data.copy()),
        MiniSeismogram(data=-np.roll(data, nroll)),
    ]
    delays, coeffs = multi_multi_delay(seismograms, abs_max=True)
    expected_delay = nroll * seismograms[0].delta
    assert delays[0, 1] == expected_delay
    assert coeffs[0, 1] < 0


def test_multi_multi_delay_different_delta_raises() -> None:
    """Mismatched sampling intervals should raise ValueError."""
    seis1 = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis2 = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis2.delta = seis1.delta * 2
    with pytest.raises(ValueError):
        multi_multi_delay([seis1, seis2])


def test_multi_multi_delay_consistent_with_multi_delay() -> None:
    """Row i of multi_multi_delay should match multi_delay(seismograms[i], seismograms)."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 7, -4, 15]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    delays_2d, coeffs_2d = multi_multi_delay(seismograms)

    for i in range(len(seismograms)):
        delays_1d, coeffs_1d = multi_delay(seismograms[i], seismograms)
        for j in range(len(seismograms)):
            assert delays_2d[i, j] == delays_1d[j]
            assert coeffs_2d[i, j] == pytest.approx(coeffs_1d[j], abs=0.05)


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_multi_multi_delay_with_seismogram(seismogram: Seismogram) -> None:
    """Test multi_multi_delay with real seismogram data and known shifts."""
    base = clone_to_mini(MiniSeismogram, seismogram)
    base.data = seismogram.data[1000:10000]
    base = detrend(base, clone=True)

    shifts = [0, 10, -20]
    seismograms = []
    for shift in shifts:
        s = clone_to_mini(MiniSeismogram, base)
        s.data = np.roll(base.data, shift)
        seismograms.append(s)

    delays, coeffs = multi_multi_delay(seismograms)

    n = len(shifts)
    assert delays.shape == (n, n)
    for i in range(n):
        for j in range(n):
            expected_delay = (shifts[j] - shifts[i]) * base.delta
            assert delays[i, j] == expected_delay
            assert coeffs[i, j] == pytest.approx(1, abs=0.05)


# --- mccc tests ---


def test_mccc_single_seismogram() -> None:
    """Single seismogram returns zero time, zero error, zero rmse."""
    seis = MiniSeismogram(data=np.sin(np.linspace(0, 4 * np.pi, 500)))
    times, errors, rmse = mccc([seis])
    assert len(times) == 1
    assert times[0].total_seconds() == 0
    assert errors[0].total_seconds() == 0
    assert rmse.total_seconds() == 0


def test_mccc_empty_list() -> None:
    """Empty list returns empty arrays and zero rmse."""
    times, errors, rmse = mccc([])
    assert len(times) == 0
    assert len(errors) == 0
    assert rmse.total_seconds() == 0


def test_mccc_known_shifts() -> None:
    """Pairwise differences should match known shifts."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 5, -10]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    times, errors, rmse = mccc(seismograms)

    assert len(times) == 3
    # times[i] - times[j] should equal delay_matrix[i, j] = (shifts[j] - shifts[i]) * delta
    for i in range(len(shifts)):
        for j in range(len(shifts)):
            expected = (shifts[j] - shifts[i]) * seismograms[0].delta
            actual = times[i] - times[j]
            assert actual.total_seconds() == pytest.approx(
                expected.total_seconds(), abs=0.1
            )


def test_mccc_zero_mean() -> None:
    """Relative times should sum to zero."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 7, -4, 15]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    times, _, _ = mccc(seismograms)

    total = sum(t.total_seconds() for t in times)
    assert total == pytest.approx(0, abs=0.1)


def test_mccc_two_identical() -> None:
    """Two identical seismograms should have zero relative delay."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    seismograms = [
        MiniSeismogram(data=data.copy()),
        MiniSeismogram(data=data.copy()),
    ]

    times, errors, rmse = mccc(seismograms)

    assert times[0].total_seconds() == pytest.approx(0, abs=1e-6)
    assert times[1].total_seconds() == pytest.approx(0, abs=1e-6)
    assert rmse.total_seconds() == pytest.approx(0, abs=1e-6)


def test_mccc_min_cc_filters_pairs() -> None:
    """Setting min_cc=1.0 with noisy data should filter all pairs, returning zeros."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    rng = np.random.default_rng(42)
    noisy = data + rng.normal(0, 5, len(data))
    seismograms = [
        MiniSeismogram(data=data.copy()),
        MiniSeismogram(data=noisy),
    ]

    times, errors, rmse = mccc(seismograms, min_cc=1.0)

    # All pairs filtered → returns zeros
    assert times[0].total_seconds() == 0
    assert times[1].total_seconds() == 0


def test_mccc_errors_are_nonnegative() -> None:
    """Standard errors should be non-negative."""
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 3, -7, 12]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    _, errors, _ = mccc(seismograms)

    for e in errors:
        assert e.total_seconds() >= 0


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_mccc_with_seismogram(seismogram: Seismogram) -> None:
    """Test mccc with real seismogram data and known shifts."""
    base = clone_to_mini(MiniSeismogram, seismogram)
    base.data = seismogram.data[1000:10000]
    base = detrend(base, clone=True)

    shifts = [0, 10, -20]
    seismograms = []
    for shift in shifts:
        s = clone_to_mini(MiniSeismogram, base)
        s.data = np.roll(base.data, shift)
        seismograms.append(s)

    times, errors, rmse = mccc(seismograms)

    # times[i] - times[j] should equal delay_matrix[i, j] = (shifts[j] - shifts[i]) * delta
    delta = base.delta
    for i in range(len(shifts)):
        for j in range(len(shifts)):
            expected = (shifts[j] - shifts[i]) * delta
            actual = times[i] - times[j]
            assert actual.total_seconds() == pytest.approx(
                expected.total_seconds(), abs=0.1
            )
