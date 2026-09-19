"""Resolving what a PROJECT.md *claims* against what is actually on disk.

The rest of the library reads metadata. This module is what makes a PROJECT.md
useful for a project made of many files: it turns ``episodesDir`` and
``filePattern`` into real paths, honoring the season and variant overrides, and
reports where the declaration and the directory disagree.

Paths are resolved against the **project root** -- the directory holding
PROJECT.md -- because a PROJECT.md is meant to be portable. Nothing here
follows an absolute path out of the project.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import ProjectFrontMatter, SeasonDefinition
from .parser import ProjectDocument

_GLOB_CHARACTERS = set("*?[")

_NUMBER_RUN = re.compile(r"(\d+)")


def _natural_key(path: Path) -> tuple[object, ...]:
    """Sort `chapter-2` before `chapter-10`, the way a person would."""
    parts = _NUMBER_RUN.split(path.name)
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)


def _root_for(
    document: ProjectDocument | None, root: str | os.PathLike[str] | None
) -> Path:
    if root is not None:
        return Path(root).expanduser()
    if document is not None and document.path is not None:
        return document.path.parent
    raise ValueError("No project root: pass root=, or parse the document from a file")


def _season_for(
    front_matter: ProjectFrontMatter, season: int | None
) -> SeasonDefinition | None:
    if season is None or not front_matter.seasons:
        return None
    return next((s for s in front_matter.seasons if s.number == season), None)


@dataclass(frozen=True, slots=True)
class ProjectLayout:
    """Where a project's files actually are.

    ``episode_files`` holds only files that exist; ``missing_files`` holds the
    explicitly-named ones that do not.
    """

    root: Path
    episodes_dir: Path
    audio_dir: Path
    patterns: tuple[str, ...]
    episode_files: tuple[Path, ...] = ()
    missing_files: tuple[Path, ...] = ()
    intro_file: Path | None = None
    outro_file: Path | None = None
    season: int | None = None

    @property
    def episode_count(self) -> int:
        return len(self.episode_files)

    def relative_episode_files(self) -> tuple[Path, ...]:
        """Episode paths relative to the project root, for display."""
        return tuple(p.relative_to(self.root) for p in self.episode_files)


def resolve_layout(
    document: ProjectDocument | ProjectFrontMatter,
    *,
    season: int | None = None,
    root: str | os.PathLike[str] | None = None,
) -> ProjectLayout:
    """Resolve a project's declared layout into real paths.

    Season-level ``episodesDir``, ``filePattern``, ``introFile``, and
    ``outroFile`` override the project-level values, matching the resolution
    order in :func:`pyproyecto.resolve_variant`.
    """
    if isinstance(document, ProjectDocument):
        front_matter = document.front_matter
        base = _root_for(document, root)
    else:
        front_matter = document
        base = _root_for(None, root)

    season_def = _season_for(front_matter, season)

    episodes_dir = base / (
        (season_def.episodes_dir if season_def else None)
        or front_matter.resolved_episodes_dir
    )
    audio_dir = base / front_matter.resolved_audio_dir

    pattern_source = (
        season_def.file_pattern
        if season_def and season_def.file_pattern
        else front_matter.file_pattern
    )
    patterns = (
        pattern_source.patterns
        if pattern_source is not None
        else front_matter.resolved_file_patterns
    )

    found: list[Path] = []
    missing: list[Path] = []
    seen: set[Path] = set()

    for pattern in patterns:
        if _GLOB_CHARACTERS & set(pattern):
            matches = sorted(episodes_dir.glob(pattern), key=_natural_key)
            for match in matches:
                if match.is_file() and match not in seen:
                    seen.add(match)
                    found.append(match)
        else:
            # An explicit filename. Its absence is worth reporting, because a
            # named file that is not there is a broken declaration, while a
            # glob that matches nothing may just be an empty season.
            candidate = episodes_dir / pattern
            if candidate.is_file():
                if candidate not in seen:
                    seen.add(candidate)
                    found.append(candidate)
            else:
                missing.append(candidate)

    def _asset(name: str | None) -> Path | None:
        # Project-resolved, per defect D7: relative to the project root, not
        # to episodesDir.
        return None if name is None else base / name

    intro = _asset(
        (season_def.intro_file if season_def else None) or front_matter.intro_file
    )
    outro = _asset(
        (season_def.outro_file if season_def else None) or front_matter.outro_file
    )

    return ProjectLayout(
        root=base,
        episodes_dir=episodes_dir,
        audio_dir=audio_dir,
        patterns=tuple(patterns),
        episode_files=tuple(found),
        missing_files=tuple(missing),
        intro_file=intro,
        outro_file=outro,
        season=season,
    )


def episode_files(
    document: ProjectDocument | ProjectFrontMatter,
    *,
    season: int | None = None,
    root: str | os.PathLike[str] | None = None,
) -> tuple[Path, ...]:
    """The project's episode files, in natural order.

    The short form of :func:`resolve_layout` for callers that only want paths.
    """
    return resolve_layout(document, season=season, root=root).episode_files


@dataclass(frozen=True, slots=True)
class LayoutAudit:
    """Where a PROJECT.md and its directory disagree."""

    layout: ProjectLayout
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    unmatched_files: tuple[Path, ...] = field(default_factory=tuple)

    @property
    def is_clean(self) -> bool:
        return not self.errors and not self.warnings


COMPOSITION_EXTENSIONS: tuple[str, ...] = (
    ".fountain",
    ".highland",
    ".fdx",
    ".guion",
    ".md",
    ".markdown",
    ".txt",
    ".rtf",
    ".pdf",
    ".docx",
    ".odt",
)
"""Extensions treated as composition files when scanning a directory."""


def audit_layout(
    document: ProjectDocument | ProjectFrontMatter,
    *,
    season: int | None = None,
    root: str | os.PathLike[str] | None = None,
) -> LayoutAudit:
    """Check a declared layout against the files that are actually there.

    This is the adoption check: point it at a project and it says whether the
    PROJECT.md describes the directory truthfully.
    """
    layout = resolve_layout(document, season=season, root=root)
    front_matter = (
        document.front_matter if isinstance(document, ProjectDocument) else document
    )

    errors: list[str] = []
    warnings: list[str] = []

    if not layout.episodes_dir.is_dir():
        errors.append(
            f"episodesDir does not exist: "
            f"{layout.episodes_dir.relative_to(layout.root)}"
        )
    else:
        for pattern in layout.patterns:
            if _GLOB_CHARACTERS & set(pattern) and not list(
                layout.episodes_dir.glob(pattern)
            ):
                warnings.append(f"filePattern {pattern!r} matches no files")

    for missing in layout.missing_files:
        errors.append(
            f"filePattern names a file that does not exist: "
            f"{missing.relative_to(layout.root)}"
        )

    season_def = _season_for(front_matter, season)
    declared = season_def.episodes if season_def else front_matter.episodes
    if (
        declared is not None
        and layout.episode_files
        and declared != layout.episode_count
    ):
        warnings.append(
            f"declares {declared} episodes but {layout.episode_count} files match"
        )

    for label, path in (
        ("introFile", layout.intro_file),
        ("outroFile", layout.outro_file),
    ):
        if path is not None and not path.is_file():
            warnings.append(f"{label} does not exist: {path.relative_to(layout.root)}")

    unmatched: tuple[Path, ...] = ()
    if layout.episodes_dir.is_dir():
        matched = set(layout.episode_files)
        candidates = [
            p
            for p in sorted(layout.episodes_dir.iterdir(), key=_natural_key)
            if p.is_file()
            and p.suffix.lower() in COMPOSITION_EXTENSIONS
            and p.name != "PROJECT.md"
            and p not in matched
        ]
        unmatched = tuple(candidates)
        if candidates:
            warnings.append(
                f"{len(candidates)} composition file(s) in "
                f"{layout.episodes_dir.relative_to(layout.root)} match no "
                "filePattern"
            )

    return LayoutAudit(
        layout=layout,
        errors=tuple(errors),
        warnings=tuple(warnings),
        unmatched_files=unmatched,
    )
