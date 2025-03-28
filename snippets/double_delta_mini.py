from pysmo import Seismogram, MiniSeismogram


def double_delta_mini(seismogram: Seismogram) -> MiniSeismogram:
    """Double the sampling interval of a seismogram.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        MiniSeismogram with double the sampling interval of input seismogram.
    """

    clone = MiniSeismogram.clone(seismogram)  # (1)!
    clone.delta *= 2
    return clone
