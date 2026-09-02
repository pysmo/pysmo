import random

import numpy as np
import pandas as pd
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from pysmo import MiniSeismogram, Seismogram
from pysmo.functions import clone_to_mini, detrend
from pysmo.tools.signal import delay, mccc, multi_delay, multi_multi_delay
from tests.conftest import mini_seismograms


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
    seismogram2.begin_time += pd.Timedelta(seconds=1)
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
        cc_delay, _ = delay(seismogram1, seismogram2, max_shift=pd.Timedelta(seconds=1))

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
        max_shift=rand_int * seismogram1.delta + pd.Timedelta(seconds=2),
    )

    assert cc_delay == rand_int * seismogram1.delta

    cc_delay, _ = delay(
        seismogram2,
        seismogram1,
        max_shift=rand_int * seismogram1.delta + pd.Timedelta(seconds=2),
    )

    assert cc_delay == -rand_int * seismogram1.delta


def test_delay_max_shift_correlation_coefficient() -> None:
    """The cc returned with `max_shift` is computed from real samples, not padding.

    Regression test: `delay` used to reuse the zero-padded working array for
    the post-alignment overlap, so the cc came out near zero even for a
    perfect match once `max_shift` was set.
    """
    rng = np.random.default_rng(0)
    base = rng.normal(size=2000)
    seismogram1 = MiniSeismogram(data=base.copy(), delta=pd.Timedelta(seconds=1))

    # positive shift: data2 lags data1 by 50 samples
    seismogram2 = MiniSeismogram(data=np.roll(base, 50), delta=pd.Timedelta(seconds=1))
    cc_delay, cc_coeff = delay(
        seismogram1, seismogram2, max_shift=pd.Timedelta(seconds=100)
    )
    assert cc_delay == pd.Timedelta(seconds=50)
    assert cc_coeff == pytest.approx(1.0)

    # negative shift: data1 lags data3 by 37 samples
    seismogram3 = MiniSeismogram(data=np.roll(base, -37), delta=pd.Timedelta(seconds=1))
    cc_delay, cc_coeff = delay(
        seismogram1, seismogram3, max_shift=pd.Timedelta(seconds=100)
    )
    assert cc_delay == pd.Timedelta(seconds=-37)
    assert cc_coeff == pytest.approx(1.0)

    # anti-correlated, polarity-insensitive
    seismogram4 = MiniSeismogram(data=-np.roll(base, 50), delta=pd.Timedelta(seconds=1))
    cc_delay, cc_coeff = delay(
        seismogram1,
        seismogram4,
        max_shift=pd.Timedelta(seconds=100),
        abs_max=True,
    )
    assert cc_delay == pd.Timedelta(seconds=50)
    assert cc_coeff == pytest.approx(-1.0)


# --- multi_delay tests ---


def test_multi_delay_empty_list() -> None:
    """
    Test `multi_delay` with an empty list of seismograms.

    Verifies that the function gracefully handles an empty input list by
    returning empty arrays for both delays and correlation coefficients.
    """
    template = MiniSeismogram(data=np.array([1.0, 2.0, 3.0, 2.0, 1.0]))
    delays, ccs = multi_delay(template, [])
    assert len(delays) == 0
    assert len(ccs) == 0


def test_multi_delay_single_identical() -> None:
    """
    Test `multi_delay` with a single identical seismogram.

    Verifies that comparing a signal to itself results in zero delay and a
    perfect correlation coefficient.
    """
    data = np.sin(np.linspace(0, 4 * np.pi, 500))
    template = MiniSeismogram(data=data.copy())
    seis = MiniSeismogram(data=data.copy())
    delays, ccs = multi_delay(template, [seis])
    assert delays[0].total_seconds() == pytest.approx(0, abs=1e-6)
    assert ccs[0] == pytest.approx(1, abs=0.05)


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
    delays, ccs = multi_delay(template, [seis])
    expected_delay = nroll * template.delta
    assert delays[0] == expected_delay
    assert ccs[0] == pytest.approx(1, abs=0.05)


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

    delays, ccs = multi_delay(template, seismograms)

    assert len(delays) == len(shifts)
    assert len(ccs) == len(shifts)
    for i, shift in enumerate(shifts):
        expected_delay = shift * template.delta
        assert delays[i] == expected_delay
        assert ccs[i] == pytest.approx(1, abs=0.05)


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
    delays, ccs = multi_delay(template, [seis], abs_max=True)
    expected_delay = nroll * template.delta
    assert delays[0] == expected_delay
    assert ccs[0] < 0


def test_multi_delay_max_shift_recovers_known_shift() -> None:
    """
    Test `multi_delay` with `max_shift` set wide enough to include the true shift.

    Verifies that restricting the search space via `max_shift` still recovers
    the correct delay when the true shift lies within the restricted range.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    nroll = 10
    seis = MiniSeismogram(data=np.roll(data, nroll))
    delays, ccs = multi_delay(template, [seis], max_shift=pd.Timedelta(seconds=20))
    expected_delay = nroll * template.delta
    assert delays[0] == expected_delay
    assert ccs[0] == pytest.approx(1, abs=0.05)


def test_multi_delay_max_shift_restricts_search() -> None:
    """
    Test that `multi_delay` confines the correlation search to `max_shift`.

    Verifies that when `max_shift` is set narrower than the true signal shift,
    the returned delay is bounded by `max_shift` rather than the (unreachable)
    true shift, confirming the search space is actually restricted rather than
    the parameter being silently ignored.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())
    nroll = 50
    seis = MiniSeismogram(data=np.roll(data, nroll))

    max_shift = pd.Timedelta(seconds=10)
    delays, _ = multi_delay(template, [seis], max_shift=max_shift)

    # For this sinusoid, correlation increases monotonically towards the
    # (excluded) true peak at nroll within this window, so the masked search
    # lands exactly on the edge. This exact value is specific to this
    # waveform/nroll/max_shift combination; if you change any of them,
    # re-derive the expected delay rather than assuming it still holds.
    assert delays[0] == max_shift


def test_multi_delay_max_shift_with_abs_max() -> None:
    """
    Test `max_shift` combined with `abs_max` (polarity-insensitive matching).

    Verifies that the absolute-value masking used for `abs_max=True` respects
    `max_shift` correctly, both when the true (anti-correlated) shift lies
    within the restricted range and when it lies outside it.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    template = MiniSeismogram(data=data.copy())

    nroll = 12
    seis = MiniSeismogram(data=-np.roll(data, nroll))
    delays, ccs = multi_delay(
        template, [seis], abs_max=True, max_shift=pd.Timedelta(seconds=20)
    )
    assert delays[0] == nroll * template.delta
    assert ccs[0] < 0

    nroll_far = 50
    seis_far = MiniSeismogram(data=-np.roll(data, nroll_far))
    max_shift = pd.Timedelta(seconds=10)
    delays_far, ccs_far = multi_delay(
        template, [seis_far], abs_max=True, max_shift=max_shift
    )
    assert delays_far[0] == max_shift
    assert ccs_far[0] < 0


def test_multi_delay_negative_max_shift_raises() -> None:
    """
    Test that `multi_delay` raises `ValueError` for a negative `max_shift`.

    `#!py delay(seismogram1, seismogram2, max_shift=...)` also rejects a
    negative `max_shift`, though only incidentally (`numpy.pad` raises on a
    negative pad width). `multi_delay` checks explicitly instead, since its
    FFT-based search has no equivalent implicit failure mode.
    """
    template = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    seis = MiniSeismogram(data=np.array([1.0, 2.0, 3.0]))
    with pytest.raises(ValueError):
        multi_delay(template, [seis], max_shift=pd.Timedelta(seconds=-1))


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

    delays, ccs = multi_delay(template, [seis_short, seis_long])

    assert len(delays) == 2
    assert len(ccs) == 2
    # The identical-length copy should have zero delay
    assert delays[1].total_seconds() == pytest.approx(0, abs=1e-6)
    assert ccs[1] == pytest.approx(1, abs=0.05)


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

    delays, ccs = multi_delay(template, seismograms)

    for i, shift in enumerate(shifts):
        expected_delay = shift * template.delta
        assert delays[i] == expected_delay
        assert ccs[i] == pytest.approx(1, abs=0.05)


# --- multi_multi_delay tests ---


def test_multi_multi_delay_empty_list() -> None:
    """
    Test `multi_multi_delay` with an empty list.

    Verifies that the function returns empty 0x0 matrices when no seismograms
    are provided.
    """
    delays, ccs = multi_multi_delay([], abs_max=False)
    assert delays.shape == (0, 0)
    assert ccs.shape == (0, 0)


def test_multi_multi_delay_single_seismogram() -> None:
    """
    Test `multi_multi_delay` with a single seismogram.

    Verifies that the function returns 1x1 matrices when a single seismogram is
    provided, as there are no pairs to compare.
    """
    seis = MiniSeismogram(data=np.sin(np.linspace(0, 4 * np.pi, 500)))
    delays, ccs = multi_multi_delay([seis], abs_max=False)
    assert delays.shape == (1, 1)
    assert ccs.shape == (1, 1)


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
    delays, ccs = multi_multi_delay(seismograms, abs_max=False)
    for i in range(len(seismograms)):
        assert delays[i, i] == pytest.approx(0, abs=1e-6)
        assert ccs[i, i] == pytest.approx(1, abs=0.05)


def test_multi_multi_delay_known_shifts() -> None:
    """
    Test `multi_multi_delay` pairwise delays for known signal shifts.

    Verifies that all pairwise relative delays `(shifts[j] - shifts[i])` are
    correctly recovered for a set of seismograms with unique shifts.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 5, -10]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    delays, ccs = multi_multi_delay(seismograms, abs_max=False)

    n = len(shifts)
    assert delays.shape == (n, n)
    assert ccs.shape == (n, n)
    delta = seismograms[0].delta
    for i in range(n):
        for j in range(n):
            expected_delay = (shifts[j] - shifts[i]) * delta
            assert delays[i, j] == expected_delay
            assert ccs[i, j] == pytest.approx(1, abs=0.05)


def test_multi_multi_delay_antisymmetric() -> None:
    """
    Test the antisymmetry of the `multi_multi_delay` delay matrix.

    Verifies that the delay of `j` relative to `i` is the negative of the
    delay of `i` relative to `j` (`delays[i, j] == -delays[j, i]`).
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 7, -4, 15]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    delays, _ = multi_multi_delay(seismograms, abs_max=False)

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
    delays, ccs = multi_multi_delay(seismograms, abs_max=True)
    expected_delay = nroll * seismograms[0].delta
    assert delays[0, 1] == expected_delay
    assert ccs[0, 1] < 0


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
        multi_multi_delay([seis1, seis2], abs_max=False)


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

    delays_2d, ccs_2d = multi_multi_delay(seismograms, abs_max=False)

    for i in range(len(seismograms)):
        delays_1d, ccs_1d = multi_delay(seismograms[i], seismograms)
        for j in range(len(seismograms)):
            assert delays_2d[i, j] == delays_1d[j]
            assert ccs_2d[i, j] == pytest.approx(ccs_1d[j], abs=0.05)


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

    delays, ccs = multi_multi_delay(seismograms, abs_max=False)

    n = len(shifts)
    assert delays.shape == (n, n)
    for i in range(n):
        for j in range(n):
            expected_delay = (shifts[j] - shifts[i]) * base.delta
            assert delays[i, j] == expected_delay
            assert ccs[i, j] == pytest.approx(1, abs=0.05)


# --- mccc tests ---


def test_mccc_single_seismogram() -> None:
    """
    Test `mccc` with a single seismogram.

    Verifies that the function returns zero relative time and zero RMSE for
    a single input, but an undefined (None) error, since there are no other
    signals to compare against and therefore no precision to estimate.
    """
    seis = MiniSeismogram(data=np.sin(np.linspace(0, 4 * np.pi, 500)))
    times, errors, rmse, cc_means, cc_stds = mccc([seis])
    assert len(times) == 1
    assert times[0].total_seconds() == 0
    assert errors[0] is None
    assert rmse.total_seconds() == 0
    assert cc_means == [1.0]
    assert cc_stds == [0.0]


def test_mccc_empty_list() -> None:
    """
    Test `mccc` with an empty list.

    Verifies that the function handles empty input gracefully by returning
    empty lists and zero RMSE.
    """
    times, errors, rmse, cc_means, cc_stds = mccc([])
    assert len(times) == 0
    assert len(errors) == 0
    assert rmse.total_seconds() == 0
    assert len(cc_means) == 0
    assert len(cc_stds) == 0


def test_mccc_known_shifts() -> None:
    """
    Test `mccc` relative time recovery for known signal shifts.

    Verifies that the differences between the calculated relative arrival times
    match the known sample shifts applied to the input signals.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    shifts = [0, 5, -10]
    seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]

    times, errors, rmse, _, _ = mccc(seismograms)

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

    times, _, _, _, _ = mccc(seismograms)

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

    times, errors, rmse, cc_means, cc_stds = mccc(seismograms)

    assert times[0].total_seconds() == pytest.approx(0, abs=1e-6)
    assert times[1].total_seconds() == pytest.approx(0, abs=1e-6)
    assert rmse.total_seconds() == pytest.approx(0, abs=1e-6)
    assert cc_means == pytest.approx([1.0, 1.0], abs=0.05)
    assert cc_stds == pytest.approx([0.0, 0.0], abs=1e-6)


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

    times, errors, rmse, _, _ = mccc(seismograms, min_cc=1.0)

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

    _, errors, _, _, _ = mccc(seismograms)

    for e in errors:
        assert e is not None
        assert e.total_seconds() >= 0


def test_mccc_abs_max() -> None:
    """
    Test `mccc` with polarity-flipped signals using `abs_max=True`.

    Verifies that the relative arrival times are correctly recovered even when
    one of the seismograms has inverted polarity, provided `abs_max=True` is
    passed to `mccc`.
    """
    # Use a simple pulse
    data = np.zeros(1000)
    data[495:505] = 1.0
    shifts = [0, 50, -30]
    # Flip the second seismogram
    seismograms = [
        MiniSeismogram(data=np.roll(data, shifts[0])),
        MiniSeismogram(data=-np.roll(data, shifts[1])),
        MiniSeismogram(data=np.roll(data, shifts[2])),
    ]

    # Without abs_max=True, CC for flipped trace should be lower because it's excluded from inversion
    # or has very low weights if CC is near 0 elsewhere.
    _, _, _, cc_means_no_abs, _ = mccc(seismograms, abs_max=False)

    # With abs_max=True, it should have high absolute CC and recover shifts
    times, _, _, cc_means, _ = mccc(seismograms, abs_max=True)

    # Verify that Trace 1 (the flipped one) has high negative correlation
    assert cc_means[1] < -0.9
    # And it should be much better than without abs_max (where it was likely ignored)
    assert abs(cc_means[1]) > abs(cc_means_no_abs[1])

    delta = seismograms[0].delta
    # If trace i is rolled by shifts[i], it arrives at shifts[i]*delta.
    # Relative time differences should match.
    for i in [0, 1, 2]:
        for j in [0, 1, 2]:
            expected_seconds = (shifts[i] - shifts[j]) * delta.total_seconds()
            actual_seconds = (times[i] - times[j]).total_seconds()
            assert actual_seconds == pytest.approx(expected_seconds, abs=0.5)


def test_mccc_statistics() -> None:
    """
    Test the correlation statistics returned by `mccc`.

    Verifies that `cc_means` and `cc_stds` correctly reflect the signal
    quality and coherence within the array.
    """
    data = np.sin(np.linspace(0, 8 * np.pi, 1000))
    # station 1 & 2 are identical, station 3 is noise
    rng = np.random.default_rng(42)
    seismograms = [
        MiniSeismogram(data=data.copy()),
        MiniSeismogram(data=data.copy()),
        MiniSeismogram(data=rng.normal(0, 1, len(data))),
    ]

    _times, _errors, _rmse, cc_means, cc_stds = mccc(seismograms)

    # Station 1 and 2 should have mean CC ~0.5 (1.0 with each other, ~0 with station 3)
    # Station 3 should have mean CC ~0 (correlated with nothing)
    assert cc_means[0] == pytest.approx(0.5, abs=0.1)
    assert cc_means[1] == pytest.approx(0.5, abs=0.1)
    assert cc_means[2] == pytest.approx(0.0, abs=0.1)

    # Standard deviation of CCs:
    # Station 1: [1.0, 0.0] -> mean 0.5, std 0.5
    # Station 3: [0.0, 0.0] -> mean 0.0, std 0.0
    assert cc_stds[0] == pytest.approx(0.5, abs=0.1)
    assert cc_stds[2] == pytest.approx(0.0, abs=0.1)


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

    times, errors, rmse, _, _ = mccc(seismograms)

    # times[i] - times[j] should equal delay_matrix[i, j] = (shifts[j] - shifts[i]) * delta
    delta = base.delta
    for i in range(len(shifts)):
        for j in range(len(shifts)):
            expected = (shifts[i] - shifts[j]) * delta
            actual = times[i] - times[j]
            assert actual.total_seconds() == pytest.approx(
                expected.total_seconds(), abs=0.1
            )


def test_multi_delay_constant_template_warns() -> None:
    """Constant template (zero std) should issue a UserWarning."""
    data = np.sin(np.linspace(0, 8 * np.pi, 100))
    template = MiniSeismogram(data=np.ones(100))
    seismograms = [MiniSeismogram(data=data)]
    with pytest.warns(UserWarning, match="zero standard deviation"):
        multi_delay(template, seismograms)


def test_multi_delay_constant_seismogram_warns() -> None:
    """Constant seismogram (zero std) should issue a UserWarning."""
    data = np.sin(np.linspace(0, 8 * np.pi, 100))
    template = MiniSeismogram(data=data)
    seismograms = [MiniSeismogram(data=np.ones(100))]
    with pytest.warns(UserWarning, match="zero standard deviation"):
        multi_delay(template, seismograms)


def test_multi_multi_delay_constant_seismogram_warns() -> None:
    """Constant seismogram (zero std) in multi_multi_delay should issue a UserWarning."""
    data = np.sin(np.linspace(0, 8 * np.pi, 100))
    seismograms = [
        MiniSeismogram(data=data),
        MiniSeismogram(data=np.ones(100)),
    ]
    with pytest.warns(UserWarning, match="zero standard deviation"):
        multi_multi_delay(seismograms, abs_max=False)


# ─────────────────────── Property-based tests ───────────────────────────────


@settings(deadline=None)
@given(seis=mini_seismograms(min_length=100, max_length=300))
def test_delay_self_is_zero(seis: MiniSeismogram) -> None:
    from pysmo.tools.signal import delay

    assume(np.std(seis.data) > 1e-2)
    cc_delay, cc_coeff = delay(seis, seis)
    assert cc_delay.total_seconds() == pytest.approx(0.0)
    assert cc_coeff == pytest.approx(1.0)


@settings(deadline=None)
@given(
    seis=mini_seismograms(min_length=200, max_length=500),
    shift=st.integers(min_value=1, max_value=20),
)
def test_delay_shift_recovery(seis: MiniSeismogram, shift: int) -> None:
    from pysmo.tools.signal import delay

    assume(np.std(seis.data) > 1e-2)
    L = len(seis.data) - shift - 10
    assume(L >= 100)
    data1 = seis.data[shift : shift + L]
    data2 = seis.data[:L]
    assume(np.std(data1) > 1e-2 and np.std(data2) > 1e-2)

    s1 = MiniSeismogram(data=data1, delta=seis.delta, begin_time=seis.begin_time)
    s2 = MiniSeismogram(data=data2, delta=seis.delta, begin_time=seis.begin_time)

    cc_delay, cc_coeff = delay(s1, s2)
    assert cc_delay == shift * seis.delta
    assert cc_coeff == pytest.approx(1.0, abs=0.01)

    cc_delay_rev, cc_coeff_rev = delay(s2, s1)
    assert cc_delay_rev == -shift * seis.delta
    assert cc_coeff_rev == pytest.approx(1.0, abs=0.01)
