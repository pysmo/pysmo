from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import filter_butter
import numpy as np


def run_cases(seis: Seismogram, expected_arr: list[list[float]]) -> None:
    y = seis.data - np.mean(seis.data)
    dt = seis.sampling_rate

    for testcase in range(1, 11):
        if testcase == 1:
            yf = filter_butter(y, dt, 'lowpass', 6.0, order=4)

        elif testcase == 2:
            yf = filter_butter(y, dt, 'highpass', 6.0, order=4)

        elif testcase == 3:
            yf = filter_butter(y, dt, 'bandpass', [4, 10], order=4)

        elif testcase == 4:
            yf = filter_butter(y, dt, 'bandstop', [8, 10])

        elif testcase == 5:
            yf = filter_butter(y, dt, 'lowpass', 6.0, passes=1, order=4)

        elif testcase == 6:
            yf = filter_butter(y, dt, 'highpass', 6.0, passes=1, order=4)

        elif testcase == 7:
            yf = filter_butter(y, dt, 'bandpass', [4, 10])

        elif testcase == 8:
            yf = filter_butter(y, dt, 'bandpass', [0.1, 1], order=4)

        elif testcase == 9:
            yf = filter_butter(y, dt, 'lowpass', 2, order=4)

        elif testcase == 10:
            yf = filter_butter(y, dt, 'highpass', 10, order=4)

        assert np.allclose(np.round(np.array(yf.data[:5]), decimals=6), expected_arr[testcase-1])


def test_filter_butter(seismograms: tuple[Seismogram, ...]) -> None:
    # make synthetic signal
    duration = 10  # seconds
    delta = 0.01   # x-axis step
    xbase = np.arange(0, duration, delta)
    noise = np.random.default_rng(seed=42).normal(0, 0.1, len(xbase))
    a = np.exp(-0.5*((xbase-3)/1)**2) - 0.3*np.exp(-0.5*((xbase-5)/1)**2) + noise
    syn_seis = MiniSeismogram(data=a, sampling_rate=delta)

    real_ans = [
                [-7.596511, 1.955841, 18.561562, 39.473595, 59.636836],
                [-14.156511, -12.708863, 2.685416, 13.773383, -8.389859],
                [-26.738503, -32.327387, -21.414475, -5.652508, 3.120521],
                [-12.484275, -0.629319, 20.166901, 41.110074, 41.442552],
                [-0.193916, -1.26874, -3.599251, -5.30619, -2.292705],
                [-7.891319, 11.499875, 14.053683, -1.921813, -24.499403],
                [-25.131938, -28.293415, -16.549553, -0.699734, 8.355388],
                [85.486872, 85.653418, 85.755602, 85.790238, 85.754264],
                [14.567715, 14.594185, 13.956519, 12.621199, 10.59913],
                [-6.796145, -5.319157, 1.983239, 6.856681, -10.7482]
            ]

    syn_ans = [
                [-0.107543, -0.131584, -0.152985, -0.170265, -0.182357],
                [-0.02312, -0.133211, 0.067581, 0.104227, -0.172474],
                [0.00792, -0.021368, -0.049273, -0.070193, -0.079677],
                [-0.140049, -0.26649, -0.07878, -0.053026, -0.33937],
                [-0.000105, -0.000953, -0.004061, -0.011138, -0.022961],
                [-0.079566, -0.083076, 0.143945, 0.09733, -0.136973],
                [0.005387, -0.022426, -0.048233, -0.068017, -0.07798],
                [-0.224856, -0.228411, -0.23194, -0.235438, -0.238901],
                [-0.089807, -0.095986, -0.101994, -0.107788, -0.113326],
                [-0.035759, -0.129834, 0.087186, 0.136916, -0.132746]
            ]

    # Run tests for real data
    for seis in seismograms:
        run_cases(seis, real_ans)

    # Run tests for synthetic data
    run_cases(syn_seis, syn_ans)
