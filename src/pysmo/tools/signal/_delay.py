from pysmo import Seismogram
from pysmo.tools.utils import to_seconds
from datetime import timedelta
from scipy.fft import rfft, irfft, next_fast_len
from scipy.linalg import lstsq, inv
from scipy.signal import correlate as _correlate
from scipy.stats.mstats import pearsonr as _pearsonr
from collections.abc import Sequence
from beartype import beartype
import numpy as np
import numpy.typing as npt
import math

__all__ = ["delay", "multi_delay", "multi_multi_delay", "mccc"]


@beartype
def _check_same_delta(
    seismogram1: Seismogram, seismogram2: Seismogram | Sequence[Seismogram]
) -> None:
    """Checks if the sampling interval (delta) of two seismograms or a seismogram and a sequence of seismograms are the same."""

    ref_delta = to_seconds(seismogram1.delta)

    for s in seismogram2 if isinstance(seismogram2, Sequence) else [seismogram2]:
        if not np.isclose(ref_delta, to_seconds(s.delta)):
            raise ValueError(f"Sampling intervals differ: {ref_delta} vs {s.delta}.")


def delay(
    seismogram1: Seismogram,
    seismogram2: Seismogram,
    total_delay: bool = False,
    max_shift: timedelta | None = None,
    abs_max: bool = False,
) -> tuple[timedelta, float]:
    """
    Cross correlates two seismograms to determine signal delay.

    This function is a wrapper around the
    [`scipy.signal.correlate`][scipy.signal.correlate] function. The default
    behaviour is to call the correlate function with `#!py mode="full"` using
    the full length data of the input seismograms. This is the most robust
    option, but also the slowest.

    If an approximate delay is known (e.g. because a particular phase is being
    targeted using a computed arrival time), the search space can be limited
    by setting the `max_shift` parameter to a value. The length of the
    seismogram data used for the cross-correlation is then set such that the
    calculated delay lies within +/- `max_shift`.

    Note:
        `max_shift` intentionally does *not* take the begin times of the
        seismograms into consideration. Thus, calling `#!py delay()` with
        `#!py total_delay=True` may return a delay that is larger than
        `max_shift`.

    Implications of setting the `max_shift` parameter are as follows:

    - This mode requires the seismograms to be of equal length.
    - If the true delay (i.e. the amount of time the seismograms _should_ be
      shifted by) lies within the `max_shift` range, and also produces the
      highest correlation, the delay time returned is identical for both
      methods.
    - If the true delay lies outside the `max_shift` range and produces the
      highest correlation, the delay time returned will be incorrect when
      `max_shift` is set.
    - In the event that the true delay lies within the `max_shift` range but
      the maximum signal correlation occurs outside, it will be correctly
      retrieved when the `max_shift` parameter is set, while not setting it
      yields an incorrect result.


    Args:
        seismogram1: First seismogram to use for cross correlation.
        seismogram2: Second seismogram to use for cross correlation.
        total_delay: Include the difference in `begin_time` in the delay.
        max_shift: Maximum (absolute) length of the delay.
        abs_max: Return the delay corresponding to absolute maximum.

    Returns:
        delay: Time delay of the second seismogram with respect to the first.
        ccnorm: Normalised cross correlation value of the overlapping
            seismograms *after* shifting (uses
            [`scipy.stats.mstats.pearsonr`][scipy.stats.mstats.pearsonr] for
            the calculation). This value ranges from -1 to 1, with 1 indicating
            a perfect correlation, 0 indicating no correlation, and -1
            indicating a perfect anti-correlation.

    Examples:
        To illustration the use of the `delay()` function, we read a seismogram
        from a SAC file and then generate a second seismogram from it by
        modifying it with a shift in the data and a shift in the begin time.
        This means the true delay is known, and we are able to compare the
        computed delays with this known delay:

        ```python
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import detrend, clone_to_mini
        >>> from pysmo.tools.signal import delay
        >>> from datetime import timedelta
        >>> import numpy as np
        >>>
        >>> # Create a Seismogram from a SAC file and detrend it:
        >>> seis1 = SAC.from_file("example.sac").seismogram
        >>> detrend(seis1)
        >>>
        >>> # Create a second seismogram from the first with
        >>> # a different begin_time and a shift in the data:
        >>> seis2 = clone_to_mini(MiniSeismogram, seis1)
        >>> nroll = 1234
        >>> seis2.data = np.roll(seis2.data, nroll)
        >>> begin_time_delay = np.timedelta64(100_000_000, 'us')  # 100 seconds
        >>> seis2.begin_time += begin_time_delay
        >>>
        >>> # The signal delay is the number of samples shifted * delta:
        >>> from pysmo.tools.utils import to_seconds
        >>> (signal_delay := nroll * seis1.delta)
        numpy.timedelta64(24680000,'us')
        >>> to_seconds(signal_delay)
        24.68
        >>>
        >>> # Call the delay function with the two seismograms and verify
        >>> # that the caclulated_delay is equal to the known signal delay:
        >>> calculated_delay, _ = delay(seis1, seis2)
        >>> calculated_delay == signal_delay
        True
        >>>
        ```

        As we know what the true delay is, we can mimic a scenario where an
        approximate delay is known prior to the cross-correlation, which can be
        used to limit the search space and speed up the calculation. Here we
        assign a value of the known signal delay plus 1 second to the
        `max_shift` parameter:

        ```python
        >>> max_shift = signal_delay + timedelta(seconds=1)
        >>> calculated_delay, _ = delay(seis1, seis2, max_shift=max_shift)
        >>> # As before, the calculated delay should be equal to the signal delay:
        >>> calculated_delay == signal_delay
        True
        >>>
        ```

        Setting `total_delay=True`, we also takes into account the difference
        in `begin_time` between the two seismograms:

        ```python
        >>> calculated_delay, _ = delay(seis1, seis2, total_delay=True, max_shift=signal_delay+timedelta(seconds=1))
        >>> # With `total_delay=True`, the calculated delay should be equal to
        >>> # the signal delay plus the begin time difference:
        >>> calculated_delay == signal_delay + (seis1.begin_time - seis2.begin_time)
        True
        >>>
        ```

        To demonstrate usage of the `abs_max` parameter, we flip the sign of
        the second seismogram data:

        ```python
        >>> seis2.data *= -1
        >>> calculated_delay, ccnorm = delay(seis1, seis2)
        >>> # Without `abs_max=True`, the calculated delay is no longer equal
        >>> # to the true signal delay (as expected):
        >>> calculated_delay == signal_delay
        False
        >>> # The normalised cross correlation value is also not very high
        >>> ccnorm
        np.float64(0.4267205)
        >>>
        >>> calculated_delay, ccnorm = delay(seis1, seis2, abs_max=True)
        >>> # with `abs_max=True`, the signal delay is again retrieved:
        >>> calculated_delay == signal_delay
        True
        >>> # And, as the signals are completely opposite, the normalised
        >>> # cross correlation value is -1:
        >>> np.testing.assert_approx_equal(ccnorm, -1)
        >>>
        ```
    """

    _check_same_delta(seismogram1, seismogram2)

    if max_shift is not None and len(seismogram1) != len(seismogram2):
        raise ValueError(
            "Input seismograms must be of equal length when using `max_shift`."
        )

    data1, data2 = seismogram1.data, seismogram2.data
    delta = seismogram1.delta

    if max_shift is not None:
        max_lag_in_samples = math.ceil(max_shift / delta)
        data1 = np.pad(data1, max_lag_in_samples)
        corr = _correlate(data1, data2, mode="valid")
    else:
        corr = _correlate(data1, data2, mode="full")

    corr_index = np.argmax(corr)

    if abs_max and np.max(corr) < -1 * np.min(corr):
        corr_index = np.argmin(corr)

    if max_shift is not None:
        shift = -int(corr_index - max_lag_in_samples)
    else:
        shift = int(len(data2) - 1 - corr_index)

    delay = shift * delta

    # find overlapping parts of seismograms after alignment
    if shift < 0:
        data1 = data1[-shift:]
    else:
        data2 = data2[shift:]
    if len(data1) > len(data2):
        data1 = data1[: len(data2)]
    else:
        data2 = data2[: len(data1)]

    covr, _ = _pearsonr(data1, data2)

    if total_delay:
        delay += seismogram1.begin_time - seismogram2.begin_time

    return delay, covr


def multi_delay(
    template: Seismogram, seismograms: Sequence[Seismogram], abs_max: bool = False
) -> tuple[npt.NDArray[np.timedelta64], npt.NDArray[np.float64]]:
    """
    Calculates delays and correlation coefficients for a list of seismograms against a template.

    This function uses FFT-based cross-correlation to efficiently compute delays
    for multiple seismograms at once against a single template. This is faster
    than calling [`delay`][pysmo.tools.signal.delay] in a loop, as the template
    FFT is computed only once.

    Args:
        template: Template seismogram object.
        seismograms: Sequence of Seismogram objects.
        abs_max: If `True`, uses absolute max correlation (polarity insensitive).

    Returns:
        delays: NumPy array of timedelta64 delays for each input seismogram
            relative to template.
        coeffs: NumPy array of correlation coefficients at maximum correlation
            for each seismogram.

    Raises:
        ValueError: If any seismogram has a different sampling rate than the template.

    Examples:
        Create a template seismogram and several shifted copies, then use
        `multi_delay` to recover the known shifts:

        ```python
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.signal import multi_delay
        >>> import numpy as np
        >>>
        >>> # Create a template seismogram with sinusoidal data:
        >>> data = np.sin(np.linspace(0, 8 * np.pi, 1000))
        >>> template = MiniSeismogram(data=data)
        >>>
        >>> # Create shifted copies (shifts in samples):
        >>> shifts = [0, 10, -5]
        >>> seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]
        >>>
        >>> # Calculate delays for all seismograms at once:
        >>> delays, coeffs = multi_delay(template, seismograms)
        >>> delays
        array([       0, 10000000, -5000000], dtype='timedelta64[us]')
        >>> delays.astype('timedelta64[s]')
        array([ 0, 10, -5], dtype='timedelta64[s]')
        >>>
        ```

        Use `abs_max=True` for polarity-insensitive matching:

        ```python
        >>> flipped = MiniSeismogram(data=-np.roll(data, 10))
        >>> delays, coeffs = multi_delay(template, [flipped], abs_max=True)
        >>> delays.astype('timedelta64[s]')
        array([10], dtype='timedelta64[s]')
        >>> coeffs[0] < 0
        True
        >>>
        ```
    """
    if not seismograms:
        return np.array([], dtype="timedelta64[us]"), np.array([], dtype=np.float64)

    _check_same_delta(template, seismograms)

    # setup dimensions & FFT length
    n_traces = len(seismograms)
    len_t = len(template)
    len_s = max(len(s.data) for s in seismograms)

    # pad to avoid circular convolution artifacts
    # (length >= len_template + len_signal - 1)
    n_fft = next_fast_len(len_s + len_t - 1)

    # pad and normalize template
    t_data = template.data
    t_mean = np.mean(t_data)
    t_std = np.std(t_data)
    if t_std == 0:
        t_std = 1.0
    template_padded = np.zeros(n_fft, dtype=float)
    template_padded[:len_t] = (t_data - t_mean) / t_std

    # normalize *before* padding to keep stats valid
    seismogram_matrix = np.zeros((n_traces, n_fft), dtype=float)
    for i, s in enumerate(seismograms):
        data = s.data
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            std = 1.0
        seismogram_matrix[i, : len(data)] = (data - mean) / std

    # forward FFT (rfft is faster for real data)
    t_freq = rfft(template_padded, n=n_fft)
    s_freq = rfft(seismogram_matrix, n=n_fft, axis=1)

    # cross-correlation in frequency domain
    cc_freq = s_freq * np.conj(t_freq)

    # inverse FFT & scale (div by len(template) for Pearson approx)
    cc_matrix = irfft(cc_freq, n=n_fft, axis=1) / len_t

    # find maxima
    if abs_max:
        max_indices = np.argmax(np.abs(cc_matrix), axis=1)
    else:
        max_indices = np.argmax(cc_matrix, axis=1)

    # convert circular indices to signed lags
    mid_point = n_fft // 2
    signed_lags = np.where(max_indices <= mid_point, max_indices, max_indices - n_fft)

    # Convert delays to timedelta64
    delta_us = int(to_seconds(template.delta) * 1_000_000)
    delays = (signed_lags * delta_us).astype("timedelta64[us]")
    coeffs = cc_matrix[np.arange(n_traces), max_indices]

    return delays, coeffs


def multi_multi_delay(
    seismograms: Sequence[Seismogram],
    abs_max: bool = False,
) -> tuple[npt.NDArray[np.timedelta64], npt.NDArray[np.float64]]:
    """
    Calculates pairwise delays and correlation coefficients for a sequence of seismograms.

    This function cross-correlates every seismogram with every other seismogram
    in the sequence using FFT-based cross-correlation. All FFTs are computed once
    and combined via broadcasting, making this significantly faster than calling
    [`delay`][pysmo.tools.signal.delay] for each pair individually.

    The result at `delays[i, j]` is the delay of seismogram `j` relative to
    seismogram `i` (treating `i` as the reference). The delay matrix is
    antisymmetric: `delays[i, j] == -delays[j, i]`, and the diagonal is zero.

    Args:
        seismograms: Sequence of Seismogram objects.
        abs_max: If `True`, uses absolute max correlation (polarity insensitive).

    Returns:
        delays: 2D array of shape `(N, N)` with delay times as timedelta64[us]
            values, where `N = len(seismograms)`.
        coeffs: 2D array of shape `(N, N)` with correlation coefficients.

    Raises:
        ValueError: If any seismogram has a different sampling rate than the others.

    Examples:
        Create seismograms with known shifts and compute all pairwise delays:

        ```python
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.signal import multi_multi_delay
        >>> import numpy as np
        >>>
        >>> data = np.sin(np.linspace(0, 8 * np.pi, 1000))
        >>> seismograms = [
        ...     MiniSeismogram(data=data.copy()),
        ...     MiniSeismogram(data=np.roll(data, 5)),
        ...     MiniSeismogram(data=np.roll(data, -10)),
        ... ]
        >>>
        >>> delays, coeffs = multi_multi_delay(seismograms)
        >>> delays.shape
        (3, 3)
        >>> # delay of seismogram 1 relative to seismogram 0:
        >>> delays[0, 1].astype('timedelta64[s]')
        np.timedelta64(5,'s')
        >>> # delay of seismogram 2 relative to seismogram 0:
        >>> delays[0, 2].astype('timedelta64[s]')
        np.timedelta64(-10,'s')
        >>> # antisymmetric: delays[i, j] == -delays[j, i]
        >>> delays[1, 0].astype('timedelta64[s]')
        np.timedelta64(-5,'s')
        >>>
        ```
    """
    n = len(seismograms)
    if n < 2:
        return (
            np.empty((n, n), dtype="timedelta64[us]"),
            np.empty((n, n), dtype=np.float64),
        )

    _check_same_delta(seismograms[0], seismograms)

    lengths = np.array([len(s.data) for s in seismograms])
    max_len = int(lengths.max())

    # pad to avoid circular convolution artifacts
    n_fft = next_fast_len(2 * max_len - 1)

    # normalize and pad all seismograms
    data_matrix = np.zeros((n, n_fft), dtype=float)
    for i, s in enumerate(seismograms):
        data = s.data
        std = np.std(data)
        if std == 0:
            std = 1.0
        data_matrix[i, : len(data)] = (data - np.mean(data)) / std

    # forward FFT (computed once for all seismograms)
    s_freq = rfft(data_matrix, n=n_fft, axis=1)

    # cross-correlation via broadcasting: (N, 1, freq) * (1, N, freq)
    # row i = reference, column j = target
    cc_freq = s_freq[np.newaxis, :, :] * np.conj(s_freq[:, np.newaxis, :])

    # inverse FFT & scale by reference length
    cc_matrix = irfft(cc_freq, n=n_fft, axis=2)
    cc_matrix /= lengths[:, np.newaxis, np.newaxis]

    # find maxima
    if abs_max:
        max_indices = np.argmax(np.abs(cc_matrix), axis=2)
    else:
        max_indices = np.argmax(cc_matrix, axis=2)

    # convert circular indices to signed lags
    mid_point = n_fft // 2
    signed_lags = np.where(max_indices <= mid_point, max_indices, max_indices - n_fft)

    # Convert delays to timedelta64
    delta_us = int(to_seconds(seismograms[0].delta) * 1_000_000)
    delays = (signed_lags * delta_us).astype("timedelta64[us]")

    # extract coefficients at max indices
    i_idx, j_idx = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    coeffs = cc_matrix[i_idx, j_idx, max_indices]

    return delays, coeffs


def mccc(
    seismograms: Sequence[Seismogram], min_cc: float = 0.5, damping: float = 0.1
) -> tuple[npt.NDArray[np.timedelta64], npt.NDArray[np.timedelta64], np.timedelta64]:
    """
    Multi-Channel Cross-Correlation (MCCC) for relative arrival times.

    Computes all pairwise cross-correlation delays using
    [`multi_multi_delay`][pysmo.tools.signal.multi_multi_delay], then solves
    for self-consistent relative time shifts using a weighted least-squares
    inversion with a zero-mean constraint and Tikhonov regularization. Pairs
    whose correlation coefficient falls below `min_cc` are excluded from the
    inversion.

    The returned `times` list sums to zero by construction, so the values
    represent relative shifts around the group mean.

    Args:
        seismograms: Sequence of Seismogram objects. All must share the same
            sampling interval.
        min_cc: Minimum correlation coefficient required to include a pair
            in the inversion.
        damping: Tikhonov regularization strength. Set to 0 to disable.

    Returns:
        times: List of relative arrival times (as `datetime.timedelta`).
        errors: List of standard errors (as `datetime.timedelta`).
        rmse: Root-mean-square error of the fit (as `datetime.timedelta`).

    Raises:
        ValueError: If any seismogram has a different sampling rate than the
            others (raised by `multi_multi_delay`).

    Examples:
        Create seismograms with known shifts and recover them with `mccc`:

        ```python
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.signal import mccc
        >>> import numpy as np
        >>>
        >>> # Build three seismograms with known shifts (in samples):
        >>> data = np.sin(np.linspace(0, 8 * np.pi, 1000))
        >>> shifts = [0, 5, -10]
        >>> seismograms = [MiniSeismogram(data=np.roll(data, s)) for s in shifts]
        >>>
        >>> # Run MCCC inversion:
        >>> times, errors, rmse = mccc(seismograms)
        >>>
        >>> # The relative times sum to approximately zero:
        >>> from pysmo.tools.utils import to_seconds
        >>> abs(sum(to_seconds(t) for t in times)) < 1e-10
        True
        >>>
        >>> # Pairwise differences recover the known shifts
        >>> # (times[i] - times[j] ≈ (shifts[j] - shifts[i]) * delta):
        >>> round(to_seconds(times[1] - times[0]))
        -5
        >>> round(to_seconds(times[2] - times[0]))
        10
        >>>
        ```

    References:
        VanDecar, J. C., and R. S. Crosson. “Determination of Teleseismic
        Relative Phase Arrival Times Using Multi-Channel Cross-Correlation and
        Least Squares.” Bulletin of the Seismological Society of America,
        vol. 80, no. 1, Feb. 1990, pp. 150–69,
        <https://doi.org/10.1785/BSSA0800010150>.
    """
    n_traces = len(seismograms)
    zero_delta = np.timedelta64(0, "us")

    if n_traces < 2:
        return (
            np.full(n_traces, zero_delta, dtype="timedelta64[us]"),
            np.full(n_traces, zero_delta, dtype="timedelta64[us]"),
            zero_delta,
        )

    delay_matrix, coeff_matrix = multi_multi_delay(seismograms)

    # Build linear system (g @ m = d)
    rows: list[np.ndarray] = []
    data_vec: list[float] = []
    weights: list[float] = []

    for i in range(n_traces):
        for j in range(i + 1, n_traces):
            cc = coeff_matrix[i, j]
            if cc < min_cc:
                continue

            # Convert timedelta64 to seconds
            lag_seconds = delay_matrix[i, j].astype("timedelta64[us]").astype(
                np.int64
            ) / 1_000_000.0

            row = np.zeros(n_traces)
            row[i] = 1.0
            row[j] = -1.0

            rows.append(row)
            data_vec.append(lag_seconds)
            weights.append(cc**2)

    if not rows:
        return (
            np.full(n_traces, zero_delta, dtype="timedelta64[us]"),
            np.full(n_traces, zero_delta, dtype="timedelta64[us]"),
            zero_delta,
        )

    g = np.array(rows)
    d = np.array(data_vec)
    w = np.array(weights)

    # Apply weights
    g_weighted = g * w[:, np.newaxis]
    d_weighted = d * w

    # Zero-mean constraint (sum of times = 0)
    constraint_weight = np.sum(w)
    g_system = np.vstack([g_weighted, np.ones(n_traces) * constraint_weight])
    d_system = np.concatenate([d_weighted, [0.0]])

    # Tikhonov regularization
    if damping > 0:
        g_system = np.vstack([g_system, damping * np.eye(n_traces)])
        d_system = np.concatenate([d_system, np.zeros(n_traces)])

    # Solve least squares
    solution, _, _, _ = lstsq(g_system, d_system)

    # Compute statistics
    predicted = g @ solution
    residuals = d - predicted
    sse = np.sum((residuals**2) * w)
    dof = max(len(d) - n_traces, 1)
    sigma_squared = sse / dof

    try:
        cov_matrix = sigma_squared * inv(g_system.T @ g_system)
        std_errors = np.sqrt(np.abs(np.diag(cov_matrix)))
    except np.linalg.LinAlgError:
        std_errors = np.zeros(n_traces)

    # Convert results to timedelta64
    times = (solution * 1_000_000).astype("timedelta64[us]")
    errors = (std_errors * 1_000_000).astype("timedelta64[us]")
    rmse = np.timedelta64(int(np.sqrt(sse / len(d)) * 1_000_000), "us")

    return times, errors, rmse
