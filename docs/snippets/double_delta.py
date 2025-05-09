from pysmo import Seismogram
from pysmo.classes import SAC
from copy import deepcopy
from typing import reveal_type  # (1)!


def double_delta(seismogram: Seismogram) -> Seismogram:
    """Double the sampling interval of a seismogram.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Seismogram with double the sampling interval of input seismogram.
    """

    clone = deepcopy(seismogram)  # (2)!
    clone.delta *= 2
    return clone


my_seis_in = SAC.from_file("testfile.sac").seismogram
my_seis_out = double_delta(my_seis_in)

reveal_type(my_seis_in)
reveal_type(my_seis_out)
