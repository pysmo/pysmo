Fundamentals
============

Data
----
Pysmo makes a clear distinction between data and results from processing. Anything that can be
derived from existing data should not be used in data structures used by pysmo. Not adhering to
this principle may introduce unnecessary inconsistencies (e.g. when different methods are used
in calculations). Similarily, we believe data should be completely unambiguous. A good example
for this is how time is often handled in seismic data; for certain tasks it may make sense to
use different *kinds* of time (e.g. relative to an event, first arrival, etc.), but in most cases
this introduces unnecessary complexity and potential for bugs (what if different kinds of times
are accidentally mixed?). Pysmo only uses absolute time, and instead relies on python's powerful
libraries for any calculations that may become necessary.

Pysmo Data Types
----------------
.. automodule:: pysmo.core.protocols
   :members:
   :undoc-members:
