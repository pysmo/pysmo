from doctest import ELLIPSIS, NORMALIZE_WHITESPACE

from sybil import Sybil
from sybil.evaluators.doctest import NUMBER
from sybil.parsers.markdown import PythonCodeBlockParser, SkipParser

from pysmo.conftest import copy_testfiles  # noqa: F401

collect_ignore = [
    "snippets/division.py",
    "snippets/division_annotated.py",
    "snippets/duck.py",
    "snippets/tutorial/season_detrend_v1.py",
    "snippets/tutorial/season_seismogram_short.py",
]
pytest_collect_file = Sybil(
    parsers=[
        PythonCodeBlockParser(
            future_imports=["print_function"],
            doctest_optionflags=ELLIPSIS + NORMALIZE_WHITESPACE + NUMBER,
        ),
        SkipParser(),
    ],
    pattern="*.md",
    fixtures=["copy_testfiles", "_syrupy_apply_ide_patches"],
).pytest()
