import numpy as np
import scipy.signal as sg   # type: ignore
from pysmo import Seismogram
import copy
from typing import Union


def filter_butter(seismogram: Seismogram, delta: float, ftype: str,
                  freq: Union[float, int, list[Union[float, int]]],
                  passes: int = 2, order: int = 2) -> Seismogram:

    """
    filters a numpy array (y) with a given sampling frequency (defined by delta),
    using scipy.signal.butter (Butterworth filter)
    type = 'lowpass','highpass','bandpass', or 'bandstop'
    if ftype is lowpass or highpass, freq = the corner frequency
    if ftype is bandpass or bandstop, freq = [fmin, fmax]
    passes = the number of times the filter is applied, setting the
    default to 2 means that the filter is applied forwards and backwards
    to ensure no phase shift if the resulting signal. For causal filters
    it is more appropriate to set passes = 1.
    order = the filter order (default = 4); a higher order implies a
    steeper drop-off beyond the frequency limits (fmin and/or fmax)
    ftype is the type of filter used, our favorite is the Butterworth filter
    Important: Make sure the mean of y is removed before using this function
    Output is the filtered version of y
    """

    seis = copy.deepcopy(seismogram)
    arr = seis.data

    if np.ndim(freq) != 1 and ftype == 'bandpass':
        print('Need two frequencies [fmin,fmax] for bandpass filter')
        print('no filter applied')
        return seis
    if passes > 2:
        print('Too many passes, passes =', passes)
        return seis

    sos = sg.butter(order, freq, btype=ftype, output='sos', fs=1/delta)
    arr = sg.sosfilt(sos, arr)
    if passes == 1:
        seis.data = np.ascontiguousarray(arr)
        return seis
    else:
        arr = sg.sosfilt(sos, arr[::-1])[::-1]  # apply in reverse
        seis.data = np.ascontiguousarray(arr)
        return seis
