from pysmo import Seismogram
from copy import deepcopy
from typing import overload, Literal
from scipy.signal import iirfilter, sosfilt, sosfiltfilt


@overload
def bandpass(
    seismogram: Seismogram,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def bandpass[T: Seismogram](
    seismogram: T,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[True],
) -> T: ...


def bandpass[T: Seismogram](
    seismogram: T,
    freqmin: float = 0.1,
    freqmax: float = 0.5,
    corners: int = 2,
    zerophase: bool = False,
    clone: bool = False,
) -> T | None:
    """
    Apply a bandpass filter to the input seismogram.

    Parameters:
        seismogram: The input seismogram to be filtered.
        freqmin: The minimum frequency of the bandpass filter (in Hz).
        freqmax: The maximum frequency of the bandpass filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If True, apply the filter in both forward and reverse directions to achieve zero phase distortion.
        clone: If True, return a new Seismogram object with the filtered data. If False, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    low = freqmin / fe
    high = freqmax / fe

    if not (0 < low < 1):
        raise ValueError(
            f"freqmin ({freqmin}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if not (0 < high < 1):
        raise ValueError(
            f"freqmax ({freqmax}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if freqmin >= freqmax:
        raise ValueError("freqmin must be less than freqmax.")

    sos = iirfilter(corners, [low, high], btype="band", ftype="butter", output="sos")

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None


@overload
def highpass(
    seismogram: Seismogram,
    freqmin: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def highpass[T: Seismogram](
    seismogram: T,
    freqmin: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[True],
) -> T: ...


def highpass[T: Seismogram](
    seismogram: T,
    freqmin: float = 0.1,
    corners: int = 2,
    zerophase: bool = False,
    clone: bool = False,
) -> T | None:
    """
    Apply a highpass filter to the input seismogram.

    Parameters:
        seismogram: The input seismogram to be filtered.
        freqmin: The minimum frequency of the highpass filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If True, apply the filter in both forward and reverse directions to achieve zero phase distortion.
        clone: If True, return a new Seismogram object with the filtered data. If False, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    low = freqmin / fe

    if not (0 < low < 1):
        raise ValueError(
            f"freqmin ({freqmin}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )

    sos = iirfilter(corners, low, btype="high", ftype="butter", output="sos")

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None


@overload
def lowpass(
    seismogram: Seismogram,
    freqmax: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def lowpass[T: Seismogram](
    seismogram: T,
    freqmax: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    clone: Literal[True] = ...,
) -> T: ...


def lowpass[T: Seismogram](
    seismogram: T,
    freqmax: float = 0.5,
    corners: int = 2,
    zerophase: bool = False,
    clone: bool = False,
) -> T | None:
    """
    Apply a lowpass filter to the input seismogram.

    Parameters:
        seismogram: The input seismogram to be filtered.
        freqmax: The maximum frequency of the lowpass filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If True, apply the filter in both forward and reverse directions to achieve zero phase distortion.
        clone: If True, return a new Seismogram object with the filtered data. If False, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    high = freqmax / fe

    if not (0 < high < 1):
        raise ValueError(
            f"freqmax ({freqmax}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )

    sos = iirfilter(corners, high, btype="low", ftype="butter", output="sos")

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None


@overload
def bandstop(
    seismogram: Seismogram,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    clone: Literal[False] = ...,
) -> None: ...


@overload
def bandstop[T: Seismogram](
    seismogram: T,
    freqmin: float = ...,
    freqmax: float = ...,
    corners: int = ...,
    zerophase: bool = ...,
    *,
    clone: Literal[True],
) -> T: ...


def bandstop[T: Seismogram](
    seismogram: T,
    freqmin: float = 0.1,
    freqmax: float = 0.5,
    corners: int = 2,
    zerophase: bool = False,
    clone: bool = False,
) -> T | None:
    """
    Apply a bandstop filter to the input seismogram.

    Parameters:
        seismogram: The input seismogram to be filtered.
        freqmin: The minimum frequency of the bandstop filter (in Hz).
        freqmax: The maximum frequency of the bandstop filter (in Hz).
        corners: The number of corners (poles) for the Butterworth filter.
        zerophase: If True, apply the filter in both forward and reverse directions to achieve zero phase distortion.
        clone: If True, return a new Seismogram object with the filtered data. If False, modify the input seismogram in place.

    Returns:
        A new Seismogram object containing the filtered data when called with `clone=True`.
    """
    fe = 0.5 / seismogram.delta.total_seconds()
    low = freqmin / fe
    high = freqmax / fe

    if not (0 < low < 1):
        raise ValueError(
            f"freqmin ({freqmin}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if not (0 < high < 1):
        raise ValueError(
            f"freqmax ({freqmax}) is invalid for sampling rate {1 / seismogram.delta.total_seconds()} Hz."
        )
    if freqmin >= freqmax:
        raise ValueError("freqmin must be less than freqmax.")

    sos = iirfilter(
        corners, [low, high], btype="bandstop", ftype="butter", output="sos"
    )

    if clone:
        seismogram = deepcopy(seismogram)

    if zerophase:
        seismogram.data = sosfiltfilt(sos, seismogram.data)
    else:
        seismogram.data = sosfilt(sos, seismogram.data)

    return seismogram if clone else None
