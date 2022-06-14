"""
Pysmo data types serve as input and output in many Pysmo functions.


A core principle of Pysmo (or more specifically Pysmo functions), is to distinguish between how data are
stored on disk, and how they are processed. Most computations will only use a small subset of the data
contained in a file. For example, a function that calculates the distance between two points (e.g. signal
source and instrument location) only needs the coordinates of these points. Other data that may be stored
in the file are irrelevant to the computation and can be ignored. It therefore makes sense to break up
the typically complex data structures used in files to simpler, more meaningful ones that serve as the
building blocks for Pysmo functions. Of course, this needs to happen in a well defined way. In Pysmo we
achieve this using `Python Protocol classes <https://docs.python.org/3/library/typing.html#typing.Protocol>`_.
These protocols define the types of data that can be used in functions much like built in types such as
integers or strings. The main considerations, benefits, and implications of this approach are:

*   The different types of input data that are available to Pysmo functions via the protocols are well
    defined and typically much simpler than the file format used to store the data, making it very
    straightforward to use, maintain and extend Pysmo.
*   Files of various formats still need to be read into python classes to be used with Pysmo,
    but the way they are allowed to be used is determined entirely by the protocols matched
    by these classes. In other words, compatibility of multiple file formats with Pysmo functions
    can be guaranteed (so much so that mixing and matching different file formats in the same
    function is seamlessly possible).
*   No need for a "native" Pysmo data class, which would likely require importing (and exporting)
    data from other formats. Instead, existing formats can be extended to become compatible with
    Pysmo protocols.
*   Since traditional file formats contain a lot of (meta)data, the corresponding data classes in
    Pysmo will often match multiple protocol types.

.. note::
    Python does not perform run-time type checking (though there are libraries that can provide this).
    There is therefore nothing stopping a user from trying to execute a function with input arguments of
    the wrong type. We therefore highly recommend adding type hints to code and testing it with
    *e.g.* `mypy <https://mypy.readthedocs.io/en/stable>`_.

The protocol classes used in pysmo are described below:
"""

from .seismogram import Seismogram
from .event import Event
from .station import Station
