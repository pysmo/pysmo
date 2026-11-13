"""Guard against heavy dependencies creeping back into lightweight imports."""

import subprocess
import sys

import pytest

HEAVY_MODULES = ("scipy.signal", "matplotlib", "pysmo.tools.iccs")


@pytest.mark.parametrize(
    "module",
    [
        "pysmo",
        "pysmo.classes",
        "pysmo.lib.io",
        "pysmo.tools",
        "pysmo.tools.azdist",
        "pysmo.tools.cache",
        "pysmo.tools.noise",
        "pysmo.tools.traveltime",
        "pysmo.tools.utils",
        "pysmo.tools.web",
    ],
)
def test_import_does_not_load_heavy_modules(module: str) -> None:
    """Importing I/O-level modules must not load plotting or signal processing."""
    code = (
        f"import sys, {module}\n"
        f"print(','.join(m for m in {HEAVY_MODULES!r} if m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
