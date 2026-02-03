from tests.conftest import TESTDATA
from pysmo.tools.signal import delay
from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import detrend, clone_to_mini
from pysmo.classes import SAC
import pytest
import pytest_cases
import numpy as np
from datetime import timedelta
import random

SACSEIS = SAC.from_file(TESTDATA["orgfile"]).seismogram
MINISEIS = MiniSeismogram(
    begin_time=SACSEIS.begin_time,
    delta=SACSEIS.delta,
    data=SACSEIS.data,
)


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
    seismogram2.begin_time += timedelta(seconds=1)
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


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
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
        cc_delay, _ = delay(seismogram1, seismogram2, max_shift=timedelta(seconds=1))

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
        max_shift=rand_int * seismogram1.delta + timedelta(seconds=2),
    )

    assert cc_delay == rand_int * seismogram1.delta

    cc_delay, _ = delay(
        seismogram2,
        seismogram1,
        max_shift=rand_int * seismogram1.delta + timedelta(seconds=2),
    )

    assert cc_delay == -rand_int * seismogram1.delta
