# The SAC Class

[SAC](<https://ds.iris.edu/ds/nodes/dmc/software/downloads/sac/>) (Seismic Analysis Code)
is a commonly used program that uses its own file format. Pysmo provides a Python class
([`SacIO`][pysmo.lib.io.sacio.SacIO]) to access data stored in these SAC files. The way
SAC names things is different from how the equivalent types are named in pysmo (e.g. the
seismogram `begin_time` is `b` in SAC). As the attributes in the `SacIO` class are named
accordingly, it too is not compatible with pysmo types. However, all is not lost: in order
to make use of the `SacIO` class, we simply need to map the `SacIO` attributes to the names
used in pysmo. This mapping happens in a new class, called [`SAC`][pysmo.classes.sac.SAC],
which provides access to all the `SacIO` attributes **and** pysmo compatible attributes.
This means there is little reason to ever use the `SacIO` class directly, and you are
encouraged to always use the `SAC` class instead when working with SAC files.

::: pysmo.classes.sac
    options:
      show_root_toc_entry: false
      allow_inspection: true
      members:
        - SAC

::: pysmo.lib.io.sacio
    options:
      heading_level: 2
      show_root_toc_entry: false
      members:
        - SacIO
