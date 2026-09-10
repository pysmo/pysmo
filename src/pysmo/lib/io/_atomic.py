"""Atomic file replacement shared by the format writers."""

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from os import PathLike
from pathlib import Path


def _current_umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


@contextmanager
def atomic_write(path: str | PathLike[str], *, suffix: str = ".tmp") -> Iterator[Path]:
    """Yield a temporary path beside *path* and atomically replace *path* on clean exit.

    On any exception the temporary file is removed and *path* is left
    untouched, so a failure mid-write cannot destroy an existing valid file.
    The target's directory must be writable and hold room for the new file
    alongside the old. When the target already exists its mode and ownership
    are carried over; a symlink target is resolved so the file it points to
    is replaced, not the link itself.

    Args:
        path: Destination file path.
        suffix: Suffix for the temporary file.

    Yields:
        Path to the temporary file to write to.
    """
    target = Path(os.path.realpath(path))
    try:
        existing: os.stat_result | None = target.stat()
    except FileNotFoundError:
        existing = None
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, suffix=suffix)
    os.close(fd)
    try:
        yield Path(tmp_name)
        if existing is not None:
            shutil.copymode(target, tmp_name)
            if hasattr(os, "chown"):
                try:
                    os.chown(tmp_name, existing.st_uid, existing.st_gid)
                except OSError:
                    # Unprivileged and not the owner: keep our own uid/gid.
                    pass
        else:
            os.chmod(tmp_name, 0o666 & ~_current_umask())
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
