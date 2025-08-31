from sybil import Sybil
from sybil.parsers.markdown import PythonCodeBlockParser, SkipParser
from pysmo.conftest import copy_testfiles  # noqa: F401


collect_ignore = [
    "snippets/division.py",
    "snippets/division_annotated.py",
    "snippets/duck.py",
    "snippets/signup.py",
]
pytest_collect_file = Sybil(
    parsers=[
        PythonCodeBlockParser(future_imports=["print_function"]),
        SkipParser(),
    ],
    pattern="*.md",
    fixtures=["copy_testfiles"],
).pytest()
