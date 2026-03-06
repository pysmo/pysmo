from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from pysmo import MiniSeismogram
from pysmo.classes import SAC
from pysmo.functions import clone_to_mini


@pytest.fixture()
def sac_files() -> Generator[list[Path], Any, None]:
    sac_files = sorted((Path(__file__).parent / "assets/").glob("*.sac"))
    yield sac_files


@pytest.fixture()
def butter_seis(
    sac_files: list[Path],
) -> Generator[dict[str, MiniSeismogram], Any, None]:
    butter_instances = {}
    for sac_file in sac_files:
        name = sac_file.name
        next if "butter" not in name else None
        sac = SAC.from_file(sac_file)
        mini = clone_to_mini(MiniSeismogram, sac.seismogram)
        butter_instances[name] = mini
    yield butter_instances
