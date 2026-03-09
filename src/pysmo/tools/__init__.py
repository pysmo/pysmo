# flake8: noqa: E402
"""Topic-specific tools that operate on pysmo types.

--8<-- [start:in-the-box]
[`pysmo.tools`][] contains higher-level, topic-specific modules that build
on [`pysmo.functions`][] and [`pysmo`][] types. Each tool groups related
functionality under its own submodule, imported via
`pysmo.tools.<tool-name>`.
--8<-- [end:in-the-box]

"""

from .iccs import IccsSeismogram, MiniIccsSeismogram

type _ToolsProto = IccsSeismogram
type _ToolsMini = MiniIccsSeismogram
