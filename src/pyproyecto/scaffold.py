"""Turning a directory of files into a PROJECT.md.

This is the adoption path. Someone has a folder of screenplays -- or any other
set of composition files -- and wants it to become a project. Scanning the
directory and proposing a PROJECT.md is faster and more accurate than writing
the front matter by hand, and it makes the layout explicit rather than implied.

Nothing here writes to disk. :func:`scaffold_project` returns a document to
review; writing is :func:`pyproyecto.write_document`, which rotates any
existing file rather than overwriting it.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .layout import COMPOSITION_EXTENSIONS, _natural_key
from .models import FilePattern, ProjectFrontMatter, SeasonDefinition
from .parser import ProjectDocument

_SEASON_DIR = re.compile(r"^(?:season[\s._-]*|s)(\d{1,3})$", re.IGNORECASE)

_SKIP_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    ".build",
    "audio",
    "voices",
    "dist",
    "build",
    ".venv",
}


@dataclass(frozen=True, slots=True)
class SeasonScan:
    """A season directory found on disk."""

    number: int
    directory: Path
    files: tuple[Path, ...]

    @property
    def episode_count(self) -> int:
        return len(self.files)


@dataclass(frozen=True, slots=True)
class DirectoryScan:
    """What a directory looks like, before any PROJECT.md exists."""

    root: Path
    episodes_dir: Path
    files: tuple[Path, ...]
    extensions: tuple[str, ...]
    seasons: tuple[SeasonScan, ...] = ()
    existing_project: Path | None = None

    @property
    def episode_count(self) -> int:
        return len(self.files)

    @property
    def is_multi_season(self) -> bool:
        return bool(self.seasons)

    @property
    def relative_episodes_dir(self) -> str:
        rel = self.episodes_dir.relative_to(self.root).as_posix()
        return rel or "."

    def file_pattern(self) -> FilePattern:
        """A pattern covering the extensions actually present."""
        if not self.extensions:
            return FilePattern(("*.fountain",), is_single=True)
        if len(self.extensions) == 1:
            return FilePattern((f"*{self.extensions[0]}",), is_single=True)
        return FilePattern(tuple(f"*{ext}" for ext in self.extensions))


def _composition_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        (
            p
            for p in directory.iterdir()
            if p.is_file()
            and p.suffix.lower() in COMPOSITION_EXTENSIONS
            and not p.name.startswith(".")
            and p.name not in ("PROJECT.md", "CAST.md", "README.md")
        ),
        key=_natural_key,
    )


def _season_directories(directory: Path) -> list[tuple[int, Path]]:
    if not directory.is_dir():
        return []
    found: list[tuple[int, Path]] = []
    for child in sorted(directory.iterdir(), key=_natural_key):
        if not child.is_dir() or child.name in _SKIP_DIRS:
            continue
        match = _SEASON_DIR.match(child.name)
        if match and _composition_files(child):
            found.append((int(match.group(1)), child))
    return found


def scan_directory(directory: str | os.PathLike[str]) -> DirectoryScan:
    """Look at a directory and work out how its composition files are arranged.

    Handles the three layouts that occur in practice: everything in the project
    root, everything in an ``episodes/`` subdirectory, and season
    subdirectories (``season-1/``, ``s02/``) under either.
    """
    root = Path(directory).expanduser()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    existing = root / "PROJECT.md"
    existing_project = existing if existing.is_file() else None

    # An `episodes/` subdirectory wins if it holds anything.
    episodes_dir = root
    for child in sorted(root.iterdir(), key=_natural_key):
        if child.is_dir() and child.name.lower() == "episodes":
            if _composition_files(child) or _season_directories(child):
                episodes_dir = child
            break

    season_dirs = _season_directories(episodes_dir)
    seasons = tuple(
        SeasonScan(number=number, directory=path, files=tuple(_composition_files(path)))
        for number, path in season_dirs
    )

    if seasons:
        files = tuple(f for season in seasons for f in season.files)
    else:
        files = tuple(_composition_files(episodes_dir))
        if not files and episodes_dir != root:
            files = tuple(_composition_files(root))
            episodes_dir = root

    extensions = tuple(
        ext for ext, _ in Counter(p.suffix.lower() for p in files).most_common()
    )

    return DirectoryScan(
        root=root,
        episodes_dir=episodes_dir,
        files=files,
        extensions=extensions,
        seasons=seasons,
        existing_project=existing_project,
    )


def _title_from(directory: Path) -> str:
    words = re.split(r"[\s._-]+", directory.resolve().name)
    return " ".join(word.capitalize() for word in words if word) or "Untitled Project"


def scaffold_project(
    directory: str | os.PathLike[str],
    *,
    author: str,
    title: str | None = None,
    description: str | None = None,
    genre: str | None = None,
    tags: tuple[str, ...] | None = None,
    created: datetime | None = None,
    audio_dir: str = "audio",
    export_format: str = "m4a",
    body: str | None = None,
) -> ProjectDocument:
    """Propose a PROJECT.md for a directory of composition files.

    The result is a :class:`~pyproyecto.ProjectDocument` in memory. Review it,
    adjust it, then write it with :func:`pyproyecto.write_document`.

    Season subdirectories become a ``seasons`` array; a flat directory becomes
    a single project. ``filePattern`` covers the extensions actually found, so
    the declaration matches the directory from the start.
    """
    scan = scan_directory(directory)

    seasons: tuple[SeasonDefinition, ...] | None = None
    if scan.seasons:
        seasons = tuple(
            SeasonDefinition(
                number=season.number,
                episodes=season.episode_count,
                episodes_dir=season.directory.relative_to(scan.root).as_posix(),
            )
            for season in sorted(scan.seasons, key=lambda s: s.number)
        )
    elif scan.files:
        seasons = (SeasonDefinition(number=1, episodes=scan.episode_count),)

    front_matter = ProjectFrontMatter(
        type="project",
        title=title or _title_from(scan.root),
        author=author,
        created=created or datetime.now(UTC),
        description=description,
        genre=genre,
        tags=tags,
        episodes_dir=scan.relative_episodes_dir,
        audio_dir=audio_dir,
        file_pattern=scan.file_pattern(),
        export_format=export_format,
        seasons=seasons,
        schema_version=None,  # stamped to the current version on write
    )

    return ProjectDocument.new(front_matter, body=body or "")
