"""PyProyecto -- read and write SwiftProyecto's PROJECT.md format.

A port of the PROJECT.md parser from SwiftProyecto (schema versions 3, 4,
and 5). Reading is faithful to the Swift implementation; writing is
non-destructive, rotating the previous file to ``PROJECT.<n>.md`` instead of
overwriting it.

    from pyproyecto import parse_file, validate

    doc = parse_file("PROJECT.md")
    print(doc.front_matter.title)
    result = validate(doc)
"""

from __future__ import annotations

from .discovery import (
    PROJECT_FILENAME,
    find_project_md,
    find_variants,
    is_master_file,
    is_single_project_file,
    is_variant_file,
    load_variant,
)
from .episodes import (
    KNOWN_VARIABLES,
    TemplateValidation,
    extract_template_variables,
    resolve_episode_path,
    validate_template,
)
from .errors import (
    ConformanceWarning,
    InvalidDateError,
    InvalidYAMLError,
    MissingRequiredFieldError,
    NoFrontMatterError,
    ProyectoError,
    VariantFileNotFoundError,
)
from .models import (
    CURRENT_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    FilePattern,
    LanguageDefinition,
    ProjectFrontMatter,
    SeasonDefinition,
    TTSConfig,
    VariantReference,
    VariantStatus,
)
from .parser import ProjectDocument, parse, parse_file
from .resolver import resolve_variant
from .settings import has_settings, settings, settings_as, with_settings
from .validator import ValidationMetadata, ValidationResult, validate
from .writer import (
    list_backups,
    next_backup_path,
    restore_backup,
    rotate,
    write_document,
    write_text,
)

__version__ = "0.1.0"

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "KNOWN_VARIABLES",
    "PROJECT_FILENAME",
    "SUPPORTED_SCHEMA_VERSIONS",
    "ConformanceWarning",
    "FilePattern",
    "InvalidDateError",
    "InvalidYAMLError",
    "LanguageDefinition",
    "MissingRequiredFieldError",
    "NoFrontMatterError",
    "ProjectDocument",
    "ProjectFrontMatter",
    "ProyectoError",
    "SeasonDefinition",
    "TTSConfig",
    "TemplateValidation",
    "ValidationMetadata",
    "ValidationResult",
    "VariantFileNotFoundError",
    "VariantReference",
    "VariantStatus",
    "__version__",
    "extract_template_variables",
    "find_project_md",
    "find_variants",
    "has_settings",
    "is_master_file",
    "is_single_project_file",
    "is_variant_file",
    "list_backups",
    "load_variant",
    "next_backup_path",
    "parse",
    "parse_file",
    "resolve_episode_path",
    "resolve_variant",
    "restore_backup",
    "rotate",
    "settings",
    "settings_as",
    "validate",
    "validate_template",
    "with_settings",
    "write_document",
    "write_text",
]
