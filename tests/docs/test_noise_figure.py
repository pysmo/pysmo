"""Regenerates and checks the Peterson noise figure in the `pysmo.tools.noise`
module docstring.

The figure is produced by `docs/snippets/tools/noise/peterson.py` (also shown
verbatim in the docs so users can copy it as a starting point). Running this
test with `PYSMO_SAVE_FIGS=true` rewrites the committed
`docs/images/tools/noise/peterson*.png`, matching the sybil-driven regeneration
of the other doc figures; otherwise the figures go to a temporary directory and
only their validity is checked.
"""

import importlib.util
import os
from pathlib import Path
from types import ModuleType

import matplotlib
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).parents[2]
SNIPPET_PATH = REPO_ROOT / "docs/snippets/tools/noise/peterson.py"
DOCS_IMAGE_DIR = REPO_ROOT / "docs/images/tools/noise"

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _load_snippet() -> ModuleType:
    assert SNIPPET_PATH.is_file(), f"snippet not found: {SNIPPET_PATH}"
    spec = importlib.util.spec_from_file_location(
        "noise_peterson_snippet", SNIPPET_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def image_dir(tmp_path: Path) -> Path:
    if os.getenv("PYSMO_SAVE_FIGS", "false").lower() == "true":
        DOCS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        return DOCS_IMAGE_DIR
    return tmp_path


@pytest.mark.usefixtures("seeded_noise_rng")
def test_peterson_figure(image_dir: Path) -> None:
    snippet = _load_snippet()
    light = image_dir / "peterson.png"
    dark = image_dir / "peterson_dark.png"

    snippet.main(outfile=str(light))
    plt.close("all")
    plt.style.use("dark_background")
    try:
        snippet.main(outfile=str(dark))
    finally:
        plt.style.use("default")
        plt.close("all")

    for path in (light, dark):
        data = path.read_bytes()
        assert data[:8] == _PNG_MAGIC, f"{path.name} is not a valid PNG"
        assert len(data) > 10_000, f"{path.name} looks truncated ({len(data)} bytes)"
