"""Verifies the `TraceSeismogram` recipe in `docs/usage/external-classes.md`.

Skipped unless `obspy` is installed, since pysmo does not (and should not)
depend on ObsPy — this recipe only demonstrates interoperability for users
who already have it. Not run in normal CI. Given a bug report against a
specific ObsPy version, install that version and run this test directly,
e.g.:

    uv run --with obspy pytest tests/docs/test_obspy_trace_recipe.py

The `TraceSeismogram` class lives in
`docs/snippets/external_classes/trace_seismogram.py` and is loaded from
there (rather than duplicated here) so the tested code and the documented
code can never drift apart.
"""

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np
import pytest

obspy = pytest.importorskip("obspy")

from pysmo.functions import detrend  # noqa: E402

SNIPPET_PATH = (
    Path(__file__).parents[2] / "docs/snippets/external_classes/trace_seismogram.py"
)


def _load_trace_seismogram_class() -> Any:
    assert SNIPPET_PATH.is_file(), f"snippet not found: {SNIPPET_PATH}"
    spec = importlib.util.spec_from_file_location("trace_seismogram", SNIPPET_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TraceSeismogram


def test_trace_seismogram_recipe() -> None:
    TraceSeismogram = _load_trace_seismogram_class()

    trace = obspy.Trace(
        data=np.array([1.0, 2.0, 3.0, 2.0, 1.0]),
        header={
            "network": "XX",
            "station": "TEST",
            "location": "",
            "channel": "HHZ",
            "starttime": "2024-01-01T00:00:00",
            "delta": 0.01,
        },
    )
    trace_seis = TraceSeismogram(trace)

    original_data = trace.data.copy()
    detrend(trace_seis)
    assert not np.array_equal(trace.data, original_data)
