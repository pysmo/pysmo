# Tools

Because of how they all work together, the scopes of pysmo's types, classes, and
functions are intentionally narrowly defined. Pysmo tools are also very much part
of pysmo, but the code that lives here is not relevant to the core functionality
of pysmo (i.e. how pysmo itself works). We chose this approach to easily group
related tasks together, and make pysmo easy to extend.

Each tool covers a particular topic, and exists in a separate module (i.e. it needs
to be imported as `from pysmo.tools import <toolname>`).
