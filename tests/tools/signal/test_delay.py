from pysmo.tools.signal import delay, multi_delay, multi_multi_delay, mccc
from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import detrend, clone_to_mini
from pytest_cases import parametrize_with_cases
import pytest
import numpy as np
from pandas import Timedelta
import random


def test_delay_basic() -> None:
    """
    Test basic cross-correlation delay calculation between two seismograms.

    Verifies that the `delay` function correctly identifies a 1-sample relative
    shift between two identical signal patterns when both seismograms share the
    same begin time.
    """
    data1 = np.array([1, 1, 1, 1, 2, 3, 4, 1, 1])
    data2 = np.array([1, 1, 1, 2, 3, 4, 1])
    seismogram1 = MiniSeismogram(data=data1)
    seismogram2 = MiniSeismogram(data=data2)
    cc_delay, cc_coeff = delay(seismogram1, seismogram2)
    assert cc_delay.total_seconds() == pytest.approx(-1)
    assert cc_coeff == pytest.approx(1)


def test_delay_with_total_delay_true() -> None:
    """
    Test delay calculation including absolute timing information.

    Verifies that when `total_delay=True`, the function accounts for differences
    in the `begin_time` of the seismograms. In this case, a 1-second relative
    signal shift is offset by a 1-second difference in start times, resulting
    in a total absolute delay of zero.
    """
    data1 = np.array([1, 1, 1, 1, 2, 3, 4, 1, 1])
    data2 = np.array([1, 1, 1, 2, 3, 4, 1])
    seismogram1 = MiniSeismogram(data=data1)
    seismogram2 = MiniSeismogram(data=data2)
    seismogram2.begin_time += Timedelta(seconds=1)
    cc_delay, cc_coeff = delay(seismogram1, seismogram2, total_delay=True)
    assert cc_delay.total_seconds() == pytest.approx(0)
    assert cc_coeff == pytest.approx(1)


def test_delay_with_abs_max_true() -> None:
    """
    Test delay calculation for signals with inverted polarity.

    Verifies that with `abs_max=True`, the `delay` function correctly identifies
    the best match even when signals are anti-correlated (negative correlation).
    """
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
    """
    Comprehensive test of the `delay` function using various signal manipulations.

    This test uses real seismogram data cases and performs the following checks:
    1. Raises `ValueError` if sampling intervals (delta) do not match.
    2. Raises `ValueError` if the requested `max_shift` is smaller than the actual delay.
    3. Correctly identifies delays when one seismogram is a truncated version of the other.
    4. Correctly identifies delays when signals are anti-correlated (using `abs_max=True`).
    5. Correctly identifies delays when one signal is circularly shifted (using `np.roll`).
    """
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
    """
    Test `multi_delay` with an empty list of seismograms.

    Verifies that the function gracefully handles an empty input list by
    returning empty arrays for both delays and correlation coefficients.
    """
    template = MiniSeismogram(data=np.array([1.0, 2.0, 3.0, 2.0, 1.0]))
    delays, coeffs = multi_delay(template, [])
    assert len(delays) == 0
    assert len(coeffs) == 0


def test_multi_delay_single_identical() -> None:
    """
    Test `multi_delay` with a single identical seismogram.

    Verifies that comparing a signal to itself results in zero delay and a
    perfect correlation coefficient.
    """
    data = np.sin(np.linspace(0, 4 * np.pi, 500))
    template = MiniSeismogram(data=data.copy())
    seis = MiniSeismogram(data=data.copy())
    delays, coeffs = multi_delay(template, [seis])
    assert delays[0].total_seconds() == pytest.approx(0, abs=1e-6)
    assert coeffs[0] == pytest.approx(1, abs=0.05)


def test_multi_delay_known_shift() -> None:
    """
    Test `multi_delay` with a single known signal shift.

    Verifies that the function correctly identifies a 10-sample shift (using
    `np.roll`) in a single target seismogram relative to the template.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    nroll = 10
    seis = MiniSeismogram(data=np.roll(data, nroll))
    delays, coeffs = multi_delay(template, [seis])
    expected_delay = nroll * template.delta
    assert delays[0] == expected_delay
    assert coeffs[0] == pytest.approx(1, abs=0.05)


def test_multi_delay_multiple_seismograms() -> None:
    """
    Test `multi_delay` with multiple seismograms having different shifts.

    Verifies that the function correctly identifies unique shifts for multiple
    seismograms in a single call, ensuring independent delay calculation for
    each item in the input list.
    """
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
    """
    Test `multi_delay` with inverted polarity signals using `abs_max=True`.

    Verifies that the function correctly identifies the signal shift even when
    the target seismogram is polarity-flipped, provided `abs_max` is enabled.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    nroll = 12
    seis = MiniSeismogram(data=-np.roll(data, nroll))
    delays, coeffs = multi_delay(template, [seis], abs_max=True)
    expected_delay = nroll * template.delta
    assert delays[0] == expected_delay
    assert coeffs[0] < 0


def test_multi_delay_different_delta_raises() -> None:
    """
    Test that `multi_delay` raises `ValueError` for mismatched sampling rates.

    Verifies that the function enforces consistency in sampling intervals (delta)
    between the template and target seismograms.
    """
    template = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis.delta = template.delta * 2
    with pytest.raises(ValueError):
        multi_delay(template, [seis])


def test_multi_delay_different_lengths() -> None:
    """
    Test `multi_delay` with seismograms of varying lengths.

    Verifies that the function can correctly handle target seismograms that
    have different numbers of samples compared to the template.
    """
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
    """
    Test `multi_delay` using real seismogram data and synthetic shifts.

    Verifies the accuracy of `multi_delay` on realistic signal data by
    applying known shifts to clones of a baseline seismogram and ensuring
    the function recovers those shifts.
    """
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
    """
    Test `multi_multi_delay` with an empty list.

    Verifies that the function returns empty 0x0 matrices when no seismograms
    are provided.
    """
    delays, coeffs = multi_multi_delay([])
    assert delays.shape == (0, 0)
    assert coeffs.shape == (0, 0)


def test_multi_multi_delay_single_seismogram() -> None:
    """
    Test `multi_multi_delay` with a single seismogram.

    Verifies that the function returns 1x1 matrices when a single seismogram is
    provided, as there are no pairs to compare.
    """
    seis = MiniSeismogram(data=np.sin(np.linspace(0, 4 * np.pi, 500)))
    delays, coeffs = multi_multi_delay([seis])
    assert delays.shape == (1, 1)
    assert coeffs.shape == (1, 1)


def test_multi_multi_delay_diagonal_zero() -> None:
    """
    Test that the diagonal of the `multi_multi_delay` matrices is correct.

    Verifies that every seismogram has zero delay and perfect correlation
    when compared with itself (the diagonal entries of the result matrices).
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    seismograms = [
        MiniSeismogram(data=data.copy()),
        MiniSeismogram(data=np.roll(data, 10)),
    ]
    delays, coeffs = multi_multi_delay(seismograms)
    for i in range(len(seismograms)):
        assert delays[i, i] == pytest.approx(0, abs=1e-6)
        assert coeffs[i, i] == pytest.approx(1, abs=0.05)


def test_multi_multi_delay_known_shifts() -> None:
    """
    Test `multi_multi_delay` pairwise delays for known signal shifts.

    Verifies that all pairwise relative delays `(shifts[j] - shifts[i])` are
    correctly recovered for a set of seismograms with unique shifts.
    """
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
    """
    Test the antisymmetry of the `multi_multi_delay` delay matrix.

    Verifies that the delay of `j` relative to `i` is the negative of the
    delay of `i` relative to `j` (`delays[i, j] == -delays[j, i]`).
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 7, -4, 15]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    delays, _ = multi_multi_delay(seismograms)

    n = len(shifts)
    for i in range(n):
        for j in range(n):
            assert delays[i, j] == -delays[j, i]


def test_multi_multi_delay_abs_max() -> None:
    """
    Test `multi_multi_delay` with polarity-flipped signals using `abs_max=True`.

    Verifies that the pairwise delay is correctly recovered even when one of
    the seismograms in the pair has inverted polarity.
    """
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
    """
    Test that `multi_multi_delay` raises `ValueError` for mismatched sampling rates.

    Verifies that the function enforces consistency in sampling intervals (delta)
    across all seismograms in the input sequence.
    """
    seis1 = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis2 = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis2.delta = seis1.delta * 2
    with pytest.raises(ValueError):
        multi_multi_delay([seis1, seis2])


def test_multi_multi_delay_consistent_with_multi_delay() -> None:
    """
    Test that `multi_multi_delay` results are consistent with `multi_delay`.

    Verifies that the pairwise results from the optimized matrix calculation
    match the results of running `multi_delay` individually for each
    seismogram as a reference.
    """
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
    """
    Test `multi_multi_delay` using real seismogram data and synthetic shifts.

    Verifies the accuracy of pairwise delay calculations on realistic signals
    by applying known shifts and checking the resulting delay matrix.
    """
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
    """
    Test `mccc` with a single seismogram.

    Verifies that the function returns zero relative time, zero error, and zero
    RMSE for a single input, as there are no other signals to compare against.
    """
    seis = MiniSeismogram(data=np.sin(np.linspace(0, 4 * np.pi, 500)))
    times, errors, rmse = mccc([seis])
    assert len(times) == 1
    assert times[0].total_seconds() == 0
    assert errors[0].total_seconds() == 0
    assert rmse.total_seconds() == 0


def test_mccc_empty_list() -> None:
    """
    Test `mccc` with an empty list.

    Verifies that the function handles empty input gracefully by returning
    empty lists and zero RMSE.
    """
    times, errors, rmse = mccc([])
    assert len(times) == 0
    assert len(errors) == 0
    assert rmse.total_seconds() == 0


def test_mccc_known_shifts() -> None:
    """
    Test `mccc` relative time recovery for known signal shifts.

    Verifies that the differences between the calculated relative arrival times
    match the known sample shifts applied to the input signals.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 5, -10]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    times, errors, rmse = mccc(seismograms)

    assert len(times) == 3
    for i in range(len(shifts)):
        for j in range(len(shifts)):
            expected = (shifts[i] - shifts[j]) * seismograms[0].delta
            actual = times[i] - times[j]
            assert actual.total_seconds() == pytest.approx(
                expected.total_seconds(), abs=0.1
            )


def test_mccc_zero_mean() -> None:
    """
    Test the zero-mean constraint of the `mccc` inversion.

    Verifies that the relative arrival times returned by MCCC sum to zero,
    ensuring they are centered around the group mean.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 7, -4, 15]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    times, _, _ = mccc(seismograms)

    total = sum(t.total_seconds() for t in times)
    assert total == pytest.approx(0, abs=0.1)


def test_mccc_two_identical() -> None:
    """
    Test `mccc` with two identical seismograms.

    Verifies that two identical signals result in zero relative delay and
    zero fitting error (RMSE).
    """
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
    """
    Test that `min_cc` correctly filters out poorly correlated pairs in `mccc`.

    Verifies that when `min_cc` is set high (e.g., 1.0) and signals are noisy,
    no pairs are included in the inversion, leading to zero relative shifts.
    """
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
    """
    Test that MCCC standard errors are physically meaningful.

    Verifies that the standard errors returned by the inversion are
    non-negative.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 3, -7, 12]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    _, errors, _ = mccc(seismograms)

    for e in errors:
        assert e.total_seconds() >= 0


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_mccc_with_seismogram(seismogram: Seismogram) -> None:
    """
    Test `mccc` using real seismogram data and synthetic shifts.

    Verifies that MCCC accurately recovers relative arrival times for realistic
    signals with known shifts applied to clones of a baseline seismogram.
    """
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
            expected = (shifts[i] - shifts[j]) * delta
            actual = times[i] - times[j]
            assert actual.total_seconds() == pytest.approx(
                expected.total_seconds(), abs=0.1
            )
