# Minimal Classes

Pysmo includes a minimal implementations of a class for each type. They are all named
using the pattern `Mini<Type>`, thus the [`Seismogram`][pysmo.types.Seismogram] type has
a corresponding [`MiniSeismogram`][pysmo.classes.mini.MiniSeismogram] class. The *Mini*
classes may be used directly to store and process data, or serve as base classes when
creating new or modifying existing classes.

::: pysmo.classes.mini.MiniHypocenter
    options:
      inherited_members: true

::: pysmo.classes.mini.MiniLocation
    options:
      inherited_members: true

::: pysmo.classes.mini.MiniSeismogram
    options:
      inherited_members: true

::: pysmo.classes.mini.MiniStation
    options:
      inherited_members: true
