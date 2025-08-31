from sybil import Sybil
from sybil.parsers.codeblock import PythonCodeBlockParser
from sybil.parsers.doctest import DocTestParser
from doctest import ELLIPSIS, NORMALIZE_WHITESPACE
from shutil import copyfile, copytree
from typing import Any, Generator
from pathlib import Path
import pytest
import os


@pytest.fixture()
def copy_testfiles(tmp_path: Path) -> Generator[None, Any, None]:
    cwd = os.getcwd()
    asset_testfile = str(
        os.path.join(os.path.dirname(__file__), "../tests/assets/testfile.sac"),
    )
    asset_iccsdir = str(
        os.path.join(os.path.dirname(__file__), "../tests/assets/iccs/")
    )
    test_testfile = str(tmp_path) + "/example.sac"
    test_iccsdir = str(tmp_path) + "/iccs-example/"
    copyfile(asset_testfile, test_testfile)
    copytree(asset_iccsdir, test_iccsdir)
    try:
        os.chdir(tmp_path)
        yield
    finally:
        os.chdir(cwd)


pytest_collect_file = Sybil(
    parsers=[
        DocTestParser(optionflags=ELLIPSIS + NORMALIZE_WHITESPACE),
        PythonCodeBlockParser(future_imports=["print_function"]),
    ],
    pattern="*.py",
    fixtures=["copy_testfiles"],
).pytest()
