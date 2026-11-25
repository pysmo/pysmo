# flake8: noqa: E402, F403
"""Rotation of seismogram components recorded at one station.

A [`Components`][pysmo.tools.components.Components] object holds two or three
seismograms recorded along known directions, each given as an
[`Orientation`][pysmo.Orientation]. From it, the same ground motion can be
computed along any other direction the components span: one at a time with
[`project`][pysmo.tools.components.Components.project], or as a new set with
[`rotate`][pysmo.tools.components.Components.rotate].

The `rotate_to_*` functions rotate to the usual named systems (Z/N/E, R/T,
Z/R/T, and L/Q/T) and return plain tuples of seismograms, in the order of
their name. The matching `*_orientations` functions return the target
orientations, which define the conventions used. The common case needs no
orientations: `rotate_to_zrt(Components.from_zne(z, n, e), backazimuth=baz)`
returns the Z, R, and T seismograms.

[`polarization`][pysmo.tools.components.polarization] returns the
principal axes of the ground motion, with its rectilinearity and planarity.

Rotation computes new components rather than modifying a seismogram, so
these functions have no `replace` keyword. Processing such as filtering,
cropping, or resampling is done on the seismograms before building a
`Components` object.
"""

from ..._utils import export_module_names

_internal_names = set(dir())

from ._components import *
from ._orientations import *
from ._polarization import *
from ._rotations import *

__all__ = [s for s in dir() if not s.startswith("_") and s not in _internal_names]

export_module_names(globals(), __name__)

del _internal_names
