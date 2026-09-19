"""Episode path templates.

The template syntax is the one the Swift *code* implements --
``<language>``, ``<season>``, ``<episode>``, ``<ext>``, with no zero-padding.
``PROJECT_MD_REFERENCE_v4.md`` documents a ``{number:03d}`` syntax that no
code has ever supported (defect D6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KNOWN_VARIABLES = ("language", "season", "episode", "ext")

_VARIABLE_RE = re.compile(r"<([a-zA-Z_][a-zA-Z0-9_]*)>")


def resolve_episode_path(
    template: str, *, language: str, season: int, episode: int, ext: str
) -> str:
    """Substitute the four known variables into ``template``."""
    return (
        template.replace("<language>", language)
        .replace("<season>", str(season))
        .replace("<episode>", str(episode))
        .replace("<ext>", ext)
    )


def extract_template_variables(template: str) -> tuple[str, ...]:
    """Every ``<name>`` placeholder in ``template``, in order."""
    return tuple(match.group(1) for match in _VARIABLE_RE.finditer(template))


@dataclass(frozen=True, slots=True)
class TemplateValidation:
    is_valid: bool
    invalid_variables: tuple[str, ...]


def validate_template(template: str) -> TemplateValidation:
    """Check a template for unknown variables.

    Unlike Swift's ``validateTemplate``, which always reports success
    (defect D9), an unknown variable makes this invalid.
    """
    invalid = tuple(
        name
        for name in extract_template_variables(template)
        if name not in KNOWN_VARIABLES
    )
    return TemplateValidation(is_valid=not invalid, invalid_variables=invalid)
