"""Finding PROJECT.md files and classifying them.

Search order follows ``ProjectDiscovery.findProjectMd``: if the starting
directory is named ``episodes``, its parent is checked first; then the
directory itself; then its parent.
"""

from __future__ import annotations

import os
from pathlib import Path

from .errors import VariantFileNotFoundError
from .models import ProjectFrontMatter, VariantReference
from .parser import ProjectDocument, parse_file
from .resolver import resolve_variant

PROJECT_FILENAME = "PROJECT.md"


def _check(directory: Path) -> Path | None:
    candidate = directory / PROJECT_FILENAME
    return candidate if candidate.is_file() else None


def find_project_md(start: str | os.PathLike[str]) -> Path | None:
    """Locate the PROJECT.md governing ``start`` (a file or a directory)."""
    origin = Path(start).expanduser()
    directory = origin if origin.is_dir() else origin.parent

    if directory.name.lower() == "episodes":
        found = _check(directory.parent)
        if found is not None:
            return found

    found = _check(directory)
    if found is not None:
        return found

    parent = directory.parent
    if parent != directory:
        found = _check(parent)
        if found is not None:
            return found

    return None


def is_master_file(front_matter: ProjectFrontMatter) -> bool:
    return bool(front_matter.variants) or (
        (front_matter.project_type or "").lower() == "overview"
    )


def is_variant_file(front_matter: ProjectFrontMatter) -> bool:
    return (
        front_matter.season is not None
        and bool(front_matter.languages)
        and (front_matter.project_type or "").lower() != "overview"
    )


def is_single_project_file(front_matter: ProjectFrontMatter) -> bool:
    return not is_master_file(front_matter) and not is_variant_file(front_matter)


def load_variant(
    reference: VariantReference, master_path: str | os.PathLike[str]
) -> ProjectFrontMatter:
    """Load one variant and resolve it against its master."""
    master_file = Path(master_path)
    master = parse_file(master_file).front_matter
    variant_file = master_file.parent / reference.path
    if not variant_file.is_file():
        raise VariantFileNotFoundError(reference.path, path=master_file)
    variant = parse_file(variant_file).front_matter
    return resolve_variant(variant, master, reference.season)


def find_variants(
    master_path: str | os.PathLike[str],
) -> list[ProjectFrontMatter]:
    """Load and resolve every variant a master file references."""
    master_file = Path(master_path)
    document: ProjectDocument = parse_file(master_file)
    return [
        load_variant(reference, master_file)
        for reference in (document.front_matter.variants or ())
    ]
