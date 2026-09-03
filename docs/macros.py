"""Documentation macros for zensical.

Exposes values derived from `pyproject.toml` so the documentation does not
repeat them.
"""

import re
import tomllib
from pathlib import Path
from typing import Any

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _fix_glightbox_double_wrap() -> None:
    """Stop glightbox wrapping mkdocstrings images in a second anchor.

    zensical's glightbox extension wraps images both in the element tree and,
    via a postprocessor, in stashed raw HTML. Docstring HTML rendered by
    mkdocstrings goes through both, so every image in an `Examples:` block ends
    up inside nested `<a class="glightbox">` tags, which the lightbox then
    shows as two slides. Every image in these docs reaches the tree processor
    (plain Markdown, or `md_in_html` figures), so disabling the postprocessor
    leaves each image wrapped exactly once.
    """
    from zensical.extensions.glightbox import GlightboxPostprocessor

    def _passthrough(self: Any, text: str) -> str:
        return text

    GlightboxPostprocessor.run = _passthrough  # type: ignore[method-assign]


_fix_glightbox_double_wrap()


def _supported_python_versions() -> list[str]:
    spec = str(tomllib.loads(_PYPROJECT.read_text())["project"]["requires-python"])
    lower = re.search(r">=\s*3\.(\d+)", spec)
    if lower is None:
        raise ValueError(f"Cannot parse requires-python: {spec!r}")
    low = int(lower.group(1))
    upper = re.search(r"<\s*3\.(\d+)", spec)
    high = int(upper.group(1)) - 1 if upper else low
    return [f"3.{minor}" for minor in range(low, high + 1)]


def _join(items: list[str]) -> str:
    if len(items) < 3:
        return " and ".join(items)
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def define_env(env: Any) -> None:
    """Register documentation variables."""
    versions = _supported_python_versions()
    env.variables["python_versions"] = versions
    env.variables["python_versions_phrase"] = _join(versions)
    env.variables["python_min"] = versions[0]
