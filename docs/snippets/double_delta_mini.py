from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import clone_to_mini


def double_delta_mini(seismogram: Seismogram) -> MiniSeismogram:
    """Double the sampling interval of a seismogram.

    Args:
        seismogram: Seismogram object.

    Returns:
        MiniSeismogram with double the sampling interval of input seismogram.
    """

    clone = clone_to_mini(MiniSeismogram, seismogram)  # (1)!
    clone.delta *= 2
    return clone
