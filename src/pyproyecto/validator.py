"""Validation, with messages kept byte-identical to SwiftProyecto's.

``ProjectValidator`` in Swift is the reference. The strings below are copied
from it so output from the two implementations can be diffed directly. Checks
PyProyecto adds beyond the reference carry a marker in
:attr:`ValidationResult.extra_warnings` instead of being mixed into
:attr:`ValidationResult.warnings`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .errors import ConformanceWarning
from .models import (
    LanguageDefinition,
    ProjectFrontMatter,
    SeasonDefinition,
)
from .parser import ProjectDocument

LEGACY_CAST_WARNING = (
    "`cast:` in PROJECT.md is no longer a recognized field (removed in schema "
    "v5). A production's cast lives in CAST.md, owned by SwiftReparto. The "
    "block is being preserved as an unknown key; run `proyecto migrate` to "
    "move it into CAST.md via `reparto import` and rewrite this file without "
    "it."
)

VALID_TYPES = ("project", "overview")


@dataclass(frozen=True, slots=True)
class ValidationMetadata:
    """Facts about the validated document."""

    schema_version: int = 3
    file_type: str = "project"
    season_count: int | None = None
    season_numbers: tuple[int, ...] | None = None
    language_count: int | None = None
    language_codes: tuple[str, ...] | None = None
    variant_count: int | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Errors, warnings, and metadata from a validation pass."""

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: ValidationMetadata = field(default_factory=ValidationMetadata)
    extra_warnings: tuple[str, ...] = ()
    conformance_warnings: tuple[ConformanceWarning, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _detect_file_type(front_matter: ProjectFrontMatter) -> str:
    has_variants = bool(front_matter.variants)
    project_type = (front_matter.project_type or "").lower()
    if has_variants or project_type == "overview":
        return "master"
    if front_matter.project_type is not None and project_type != "project":
        return "variant"
    return "project"


def _validate_seasons(
    seasons: Sequence[SeasonDefinition], errors: list[str], warnings: list[str]
) -> None:
    numbers = [s.number for s in seasons]
    if len(set(numbers)) < len(numbers):
        duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
        errors.append(
            "Duplicate season numbers: " + ", ".join(str(n) for n in duplicates)
        )
    for season in seasons:
        if season.episodes <= 0:
            errors.append(
                f"Season {season.number} must have episodes > 0, got {season.episodes}"
            )
        if season.number <= 0:
            errors.append(f"Season number must be positive, got {season.number}")


def _validate_languages(
    languages: Sequence[LanguageDefinition], errors: list[str]
) -> None:
    codes = [lang.code for lang in languages]
    if len(set(codes)) < len(codes):
        duplicates = sorted({c for c in codes if codes.count(c) > 1})
        errors.append("Duplicate language codes: " + ", ".join(duplicates))
    for language in languages:
        if not language.code:
            errors.append("Language code cannot be empty")


def validate(
    document: ProjectDocument | ProjectFrontMatter,
) -> ValidationResult:
    """Validate front matter, or a whole document."""
    if isinstance(document, ProjectDocument):
        front_matter = document.front_matter
        conformance = document.warnings
        leading_text = document.leading_text
    else:
        front_matter = document
        conformance = ()
        leading_text = ""

    errors: list[str] = []
    warnings: list[str] = []
    extra: list[str] = []

    schema_version = front_matter.detected_schema_version
    file_type = _detect_file_type(front_matter)

    if not front_matter.title:
        errors.append("Missing or empty title field")
    if not front_matter.author:
        errors.append("Missing or empty author field")

    if front_matter.type.lower() not in VALID_TYPES:
        errors.append(
            f'Invalid type "{front_matter.type}" — must be "project" or "overview"'
        )

    if schema_version >= 4:
        project_type = (front_matter.project_type or "project").lower()
        if project_type == "overview":
            if front_matter.variants is None:
                warnings.append("Overview files should define a 'variants' array")
            if front_matter.episodes_dir is not None:
                warnings.append(
                    "Overview files should not define 'episodesDir' — "
                    "that belongs in variants or projects"
                )
        if front_matter.seasons:
            _validate_seasons(front_matter.seasons, errors, warnings)
        if front_matter.languages:
            _validate_languages(front_matter.languages, errors)
    else:
        if front_matter.season is not None:
            if front_matter.season <= 0:
                warnings.append(
                    f"Season number should be positive: {front_matter.season}"
                )
            if front_matter.episodes is not None and front_matter.episodes <= 0:
                warnings.append(
                    f"Episode count should be positive: {front_matter.episodes}"
                )

    if front_matter.has_legacy_cast_key:
        warnings.append(LEGACY_CAST_WARNING)

    # -- checks beyond the Swift reference --------------------------------

    if leading_text.strip():
        extra.append(
            "Content appears before the opening '---'; front matter should "
            "start on line 1"
        )
    if front_matter.schema_version is not None and front_matter.schema_version > 5:
        extra.append(
            f"Unknown schemaVersion {front_matter.schema_version}; parsed with "
            "the schema v5 rules"
        )
    extra.extend(str(w) for w in conformance)

    metadata = ValidationMetadata(
        schema_version=schema_version,
        file_type=file_type,
        season_count=None
        if front_matter.seasons is None
        else len(front_matter.seasons),
        season_numbers=(
            None
            if front_matter.seasons is None
            else tuple(sorted(s.number for s in front_matter.seasons))
        ),
        language_count=(
            None if front_matter.languages is None else len(front_matter.languages)
        ),
        language_codes=(
            None
            if front_matter.languages is None
            else tuple(sorted(lang.code for lang in front_matter.languages))
        ),
        variant_count=(
            None if front_matter.variants is None else len(front_matter.variants)
        ),
    )

    return ValidationResult(
        errors=tuple(errors),
        warnings=tuple(warnings),
        metadata=metadata,
        extra_warnings=tuple(extra),
        conformance_warnings=tuple(conformance),
    )
