"""Tests for pysmo.lib.io._atomic."""

import sys
from pathlib import Path

import pytest

from pysmo.lib.io._atomic import atomic_write


def test_atomic_write_replaces_target(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_text("old")

    with atomic_write(target) as tmp:
        tmp.write_text("new")

    assert target.read_text() == "new"
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_leaves_target_intact_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.write_text("old")

    with pytest.raises(RuntimeError):
        with atomic_write(target) as tmp:
            tmp.write_text("partial")
            raise RuntimeError("boom")

    assert target.read_text() == "old"
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_creates_new_file(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"

    with atomic_write(target) as tmp:
        tmp.write_text("new")

    assert target.read_text() == "new"


def test_atomic_write_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        with atomic_write(tmp_path / "nope" / "out.txt"):
            pass


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX permission bits not meaningful on Windows"
)
def test_atomic_write_preserves_mode_of_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    target.touch()
    target.chmod(0o640)

    with atomic_write(target) as tmp:
        tmp.write_text("new")

    assert target.stat().st_mode & 0o777 == 0o640


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlink creation needs privileges on Windows"
)
def test_atomic_write_follows_symlink_target(tmp_path: Path) -> None:
    real = tmp_path / "real.txt"
    real.write_text("old")
    link = tmp_path / "link.txt"
    link.symlink_to(real)

    with atomic_write(link) as tmp:
        tmp.write_text("new")

    assert link.is_symlink()
    assert real.read_text() == "new"
