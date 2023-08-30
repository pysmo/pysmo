# The SAC Class

[SAC](<https://ds.iris.edu/ds/nodes/dmc/software/downloads/sac/>) (Seismic Analysis Code)
is a commonly used program that uses it's own file format. Pysmo provides a Python class
to access SAC files.

::: pysmo.classes.sac
    options:
      show_root_toc_entry: false
      allow_inspection: true
      members:
        - SAC
        - _SacSeismogram
        - _SacStation
        - _SacEvent


::: pysmo.lib.io.sacio
    options:
      heading_level: 2
      show_root_toc_entry: false
      members:
        - SacIO
