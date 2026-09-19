"""Error hierarchy for PyProyecto.

Every error carries the source path when one is known, and every YAML-level
error carries a line/column when the loader reports one. The Swift reference
implementation exposes neither (see REQUIREMENTS.md F8).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ProyectoError(Exception):
    """Base class for every error raised by PyProyecto."""

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}" if path else message)


class NoFrontMatterError(ProyectoError):
    """The document has no ``---`` ... ``---`` front matter block."""

    def __init__(self, *, path: Path | None = None) -> None:
        super().__init__(
            "No YAML front matter found (must be delimited by ---)", path=path
        )


class InvalidYAMLError(ProyectoError):
    """The front matter is not loadable, or a value has the wrong type."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self.line = line
        self.column = column
        where = f" (line {line}, column {column})" if line is not None else ""
        super().__init__(f"Invalid YAML: {message}{where}", path=path)


class MissingRequiredFieldError(ProyectoError):
    """A required key is absent.

    ``field`` is a dotted path (``seasons[1].episodes``); Swift reports only
    the leaf key.
    """

    def __init__(self, field: str, *, path: Path | None = None) -> None:
        self.field = field
        super().__init__(f"Missing required field: {field}", path=path)


class InvalidDateError(ProyectoError):
    """A date value is not a timezone-aware ISO 8601 timestamp."""

    def __init__(self, field: str, value: object, *, path: Path | None = None) -> None:
        self.field = field
        self.value = value
        super().__init__(
            f"Invalid date format for {field}: {value!r} "
            "(expected ISO 8601 with a timezone, e.g. 2025-01-25T00:00:00Z)",
            path=path,
        )


class VariantFileNotFoundError(ProyectoError):
    """A ``variants[].path`` entry points at a file that does not exist."""

    def __init__(self, variant_path: str, *, path: Path | None = None) -> None:
        self.variant_path = variant_path
        super().__init__(f"Variant file not found: {variant_path}", path=path)


@dataclass(frozen=True, slots=True)
class ConformanceWarning:
    """A document that PyProyecto accepts but the Swift reference does not.

    Emitted where REQUIREMENTS.md open question 3 chose leniency over bug
    parity. ``swift_defect`` names the entry in the defect table.
    """

    field: str
    message: str
    swift_defect: str

    def __str__(self) -> str:
        return f"{self.field}: {self.message} [{self.swift_defect}]"
