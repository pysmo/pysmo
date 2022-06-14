"""
The Pysmo package provides tools for seismologists to solve problems in a pythonic fashion.

Pysmo aims to simplify processing of seismic data by using sensible data types instead of
complicated and convoluted data structures typically used in various file formats. Instead
of relying on Python data classes [#]_ that essentially mirror the file formats, Pysmo functions
use much simpler and meaningful data types. They are defined with processing in mind (rather
than e.g. archiving), resulting in these key benefits:

    - Pysmo functions (i.e. Python functions using Pysmo) use well defined in- and outputs
      instead of indiscriminately using large dictionary or database like Python classes,
      of which only a small portion is typically needed by the function.
    - Pysmo is easily extendible: new data types or functions for processing can be added
      without affecting existing code, and the existing ones can serve as building blocks
      to solve more complex problems.
    - Pysmo is not written with a particular file format or its respective Python data class
      in mind (nor does it invent yet another one). It therefore is less sensitive to
      potential changes in existing file formats, new formats becoming the commonly used
      standard etc.

Essentially, instead of functions needing to be compatible with Python data classes derived
from file formats, Pysmo requires these classes to be compatible with the functions. Consider
for example a hypothetical file format that contains station and event data, as well as a
seismogram (:numref:`fig_hypothetical_file`). Calculating the great circle distance (gcd)
requires information about the station and the event, while the seismogram is unnecessary data.
Traditionally, all data are passed as a single argument to Python functions, whereas in Pysmo
functions are more explicit about what data they require for the same calculation.

  .. _fig_hypothetical_file:
  .. figure:: images/hypothetical_file.drawio.png
     :align: center
     :alt: TODO: Alternative text only image

     Instead of consuming the entire data class, Pysmo functions only use information they
     actually need for a calculation.

In the above example the same input file was used for both the traditional and the Pysmo functions,
and both methods perform the task of calculating the great circle distance equally well. Thus the
differences between the two methods might seem quite small. However, besides having a slightly
different syntax (which we believe to be a good thing in of itself), the Pysmo functions have the
major advantage of not being strongly coupled to the often complicated structures present in file
formats. If we again assume a hypothetical file format, but this time without the file containing
seismogram data, the Pysmo function can still be used. The traditional function will fail because
it depends on input data that contains a seismogram (:numref:`fig_hypothetical_file_without_seismogram`).


  .. _fig_hypothetical_file_without_seismogram:
  .. figure:: images/hypothetical_file_without_seismogram.drawio.png
     :align: center
     :alt: TODO: Alternative text only image

     Even though not required for the calculation itself, the traditional function will fail if
     there is no seismogram in the input.

Of course, the main reason why the traditional function fails is likely more due to the differences
between the file formats than lack of seismogram data. As a different file format would probably also
store station and event data differently, the Pysmo function would face similar problems. This is
addressed in a later chapter (:ref:`fundamentals:pysmo data types`). The point we are making here is
that functions are better written with the data they need in mind, rather than the data they are given.
Besides making code easier to maintain when underlying file formats change (or new ones are added),
there are additional benefits to this approach. We illustrate some of them in :numref:`fig_pysmo_benefits`.

  .. _fig_pysmo_benefits:
  .. figure:: images/pysmo_benefits.drawio.png
     :align: center
     :alt: TODO: Alternative text only image

     Examples of how Pysmo functions can be used in novel ways: (a) If a function needs data that is not
     present in a file format, the file can be used in combination with external data to perform the
     computation. (b) Using synthetic seismograms with Pysmo functions is straightforward, as there is no
     need to add all the extra (meta)data to turn it into a particular file format for further use. (c)
     Functions can directly use data from different file types in the same function.

Splitting up traditional data classes into these :ref:`fundamentals:pysmo data types`, we are able to
provide essential :ref:`functions:functions`, which are easy to use and in turn serve as building blocks
to write more complex :ref:`tools:tools`.

.. rubric:: Footnotes

.. [#] In this discussion "data classes" simply refers to a class containing (seismological) data, and not
   the Python `dataclasses module <https://docs.python.org/3/library/dataclasses.html>`_.
"""

from importlib.metadata import version
from pysmo.core.sac.sacio import _SacIO  # noqa: F401
from pysmo.core.sac.sac import SAC  # noqa: F401
from pysmo.core.protocols import *  # noqa: F401,F403
from pysmo.core.functions import *  # noqa: F401,F403

__version__ = version('pysmo')
