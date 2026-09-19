"""Writing PROJECT.md without ever destroying the previous version.

Every write rotates the file that is already on disk to ``<stem>.<n><ext>`` --
``PROJECT.md`` becomes ``PROJECT.1.md``, then ``PROJECT.2.md``, and so on --
before the new content takes its place. Nothing is overwritten and nothing is
pruned, so a bad write is always one rename away from being undone.

The new file is written to a temporary file in the same directory and then
moved into place, so a reader never sees a half-written PROJECT.md.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Sequence
from pathlib import Path

from .parser import ProjectDocument


def _backup_pattern(path: Path) -> re.Pattern[str]:
    stem = re.escape(path.stem)
    suffix = re.escape(path.suffix)
    return re.compile(rf"^{stem}\.(\d+){suffix}$")


def list_backups(path: str | os.PathLike[str]) -> list[Path]:
    """Existing rotated backups of ``path``, oldest first."""
    target = Path(path)
    pattern = _backup_pattern(target)
    directory = target.parent if str(target.parent) else Path(".")
    if not directory.is_dir():
        return []
    numbered: list[tuple[int, Path]] = []
    for candidate in directory.iterdir():
        match = pattern.match(candidate.name)
        if match:
            numbered.append((int(match.group(1)), candidate))
    return [p for _, p in sorted(numbered)]


def next_backup_path(path: str | os.PathLike[str]) -> Path:
    """The path the current file would be rotated to.

    Numbering is always ``max(existing) + 1``, so deleting an old backup never
    causes a later write to reuse its number.
    """
    target = Path(path)
    pattern = _backup_pattern(target)
    highest = 0
    for existing in list_backups(target):
        match = pattern.match(existing.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return target.with_name(f"{target.stem}.{highest + 1}{target.suffix}")


def rotate(path: str | os.PathLike[str]) -> Path | None:
    """Move an existing file aside to its next backup path.

    Returns the backup path, or ``None`` when there was nothing to rotate.
    """
    target = Path(path)
    if not target.exists():
        return None
    backup = next_backup_path(target)
    os.replace(target, backup)
    return backup


def write_text(
    path: str | os.PathLike[str], text: str, *, backup: bool = True
) -> Path | None:
    """Write ``text`` to ``path``, rotating any existing file first.

    Returns the backup path, or ``None`` if no backup was made.
    """
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    # Stage the new content first: if this fails, the original is untouched.
    descriptor, staged_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    staged = Path(staged_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        backup_path = rotate(target) if backup else None
        os.replace(staged, target)
        return backup_path
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


def write_document(
    document: ProjectDocument,
    path: str | os.PathLike[str] | None = None,
    *,
    backup: bool = True,
) -> Path | None:
    """Write a document to ``path`` (defaults to where it was parsed from).

    Returns the backup path, or ``None`` if no backup was made.
    """
    target = Path(path) if path is not None else document.path
    if target is None:
        raise ValueError(
            "No destination: pass a path, or parse the document from a file"
        )
    return write_text(target, document.to_text(), backup=backup)


def restore_backup(
    path: str | os.PathLike[str], backup: str | os.PathLike[str] | None = None
) -> Path:
    """Put a rotated backup back, rotating the current file in its turn.

    With no ``backup`` given, the most recent one is used. The file being
    replaced is itself rotated, so an undo is as reversible as the write was.
    """
    target = Path(path)
    if backup is None:
        backups: Sequence[Path] = list_backups(target)
        if not backups:
            raise FileNotFoundError(f"No backups found for {target}")
        source = backups[-1]
    else:
        source = Path(backup)
        if not source.exists():
            raise FileNotFoundError(f"Backup not found: {source}")
    write_text(target, source.read_text(encoding="utf-8"), backup=True)
    return target
