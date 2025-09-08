from pysmo import Seismogram
from pysmo.classes import SAC
from pathlib import Path
from copy import deepcopy
from typing import reveal_type


def double_delta_generic[T: Seismogram](seismogram: T) -> T:  # (1)!
    """Double the sampling interval of a seismogram.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Seismogram with double the sampling interval of input seismogram.
    """

    clone = deepcopy(seismogram)
    clone.delta *= 2
    return clone


sacfile = Path("example.sac")
my_seis_in = SAC.from_file(sacfile).seismogram
my_seis_out = double_delta_generic(my_seis_in)

reveal_type(my_seis_in)
reveal_type(my_seis_out)
