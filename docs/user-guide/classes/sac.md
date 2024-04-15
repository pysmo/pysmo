# The SAC Classes

[SAC](<https://ds.iris.edu/ds/nodes/dmc/software/downloads/sac/>) (Seismic Analysis Code)
is a commonly used program that uses its own file format. The names, conventions, types,
as well as the large number of "header" fields (metadata) mean the structure within SAC
files is very different from the types pysmo uses. To use SAC files with pysmo therefore
requires not only reading a SAC file into a Python object, but also translating SAC
header fields so that they can be accessed as pysmo types. Pysmo provides two classes
for this:

  1. [`SacIO`][pysmo.lib.io.sacio.SacIO] to read SAC files and access data and headers
     using the same formats and naming conventions as used in the SAC file format.
  2. [`SAC`][pysmo.classes.sac.SAC] to translate data stored in SAC header fields so that
     they become compatible with pysmo types.


::: pysmo.classes.sac
    options:
      show_root_toc_entry: false
      allow_inspection: true
      members:
        - SAC


## SAC helper classes

The SAC helper classes make it possible to use data stored in SAC files
with pysmo types. Instances of each helper class are created in
[`SAC`][pysmo.classes.sac.SAC] objects, which serve as containers for
the helper classes. For example, an instance of
[`SacSeismogram`][pysmo.classes.sac.SacSeismogram] is created as
`<SAC-object>.seismogram`, an instance of [`SacStation`][pysmo.classes.sac.SacStation]
as `<SAC-object>.station`, and so on:

```python
>>> from pysmo import SAC, Seismogram, Station
>>> my_sac = SAC.from_file("testfile.sac")
>>> isinstance(my_sac.seismogram, Seismogram) # (1)!
True
>>> isinstance(my_sac.station, Station) # (2)!
True
>>>
```

1.  `my_sac.seismogram` is an instance of [`SacSeismogram`][pysmo.classes.sac.SacSeismogram]
    and is therefore compatible with the
    [`Seismogram`][pysmo.types.Seismogram] type.
2.  `my_sac.station` is an instance of [`SacStation`][pysmo.classes.sac.SacStation]
    and is therefore compatible with the
    [`Station`][pysmo.types.Station] type.

!!! note
    It is possible to instantiate SAC helper objects manually from a
    [`SacIO`][pysmo.lib.io.sacio.SacIO] object:

    ```python
    >>> from pysmo import Seismogram
    >>> from pysmo.lib.io.sacio import SacIO
    >>> from pysmo.classes.sac import SacSeismogram
    >>> my_sacio = SacIO.from_file("testfile.sac")
    >>> my_seismogram = SacSeismogram(parent=my_sacio)
    >>> isinstance(my_seismogram, Seismogram)
    True
    >>>
    ```

    This avoids having to type `my_sac.seismogram`, and one
    can instead use `my_seismogram`. However, since the same
    effect can be achieved by creating a
    [`SAC`][pysmo.classes.sac.SAC] object more easily, we
    recommend the following approach:

    ```python
    >>> from pysmo import SAC, Seismogram
    >>> my_sac = SAC.from_file("testfile.sac")
    >>> my_seismogram = my_sac.seismogram
    >>> isinstance(my_seismogram, Seismogram)
    True
    >>>
    ```

::: pysmo.classes.sac
    options:
      heading_level: 3
      show_root_toc_entry: false
      allow_inspection: true
      show_inheritance: false
      members:
        - SacSeismogram
        - SacStation
        - SacEvent
        - SacTimestamps


::: pysmo.lib.io.sacio
    options:
      heading_level: 2
      show_root_toc_entry: false
      members:
        - SacIO
