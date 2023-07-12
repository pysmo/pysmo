from pysmo import MiniSeismogram
from pysmo.functions import xcorr
import numpy as np


def test_xcorr() -> None:
    duration = 100  # seconds
    delta = 0.025   # x-axis step
    xbase = np.arange(0, duration, delta)
    noise = np.random.default_rng(seed=42).normal(0, 0.2, len(xbase))
    a = np.exp(-0.5*((xbase-12)/1)**2) - 0.3*np.exp(-0.5*((xbase-16)/1)**2) + noise

    for testcase in range(3):
        if testcase == 0:
            x = xbase
            v = np.exp(-0.5*((x-18)/1)**2)
            m = 400   # samples in maximum lag duration
            expected_arr = [0.039453, 0.040382, 0.041337, 0.042319, 0.043331,
                            0.044373, 0.045447, 0.046555, 0.047698, 0.048879]

        if testcase == 1:
            ind = round(len(xbase)/8)
            x = xbase[ind:-ind]
            v = np.exp(-0.5*((x-18)/1)**2)
            m = round(0.5*(len(a)-len(v)))
            expected_arr = [-0.006293, -0.006286, -0.006272, -0.006248, -0.006215,
                            -0.006173, -0.006121, -0.006059, -0.005986, -0.005902]

        if testcase == 2:
            x = np.arange(-17, duration+17, delta)
            v = np.exp(-0.5*((x-18)/1)**2)
            m = round(0.5*(len(v)-len(a)))
            expected_arr = [-0.002352, -0.002758, -0.003177, -0.003607, -0.004049,
                            -0.004502, -0.004965, -0.005439, -0.005922, -0.006414]

        seis1, seis2 = MiniSeismogram(data=a), MiniSeismogram(data=v)
        corr_arr = xcorr(seis1, seis2, m)

        assert np.allclose(np.round(corr_arr[:10], decimals=6), expected_arr)
