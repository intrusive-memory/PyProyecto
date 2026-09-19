"""App-specific settings sections.

The Python equivalent of ``AppFrontMatterSettings``: an app claims a top-level
key in the front matter and stores whatever it likes under it. Settings live
in :attr:`ProjectFrontMatter.extra`, so they survive a read-write cycle even
when no one asks for them by type.

    @dataclass(frozen=True)
    class MyAppSettings:
        section_key: ClassVar[str] = "myapp"
        theme: str | None = None
        auto_save: bool | None = None

    settings = settings_as(front_matter, MyAppSettings)
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from .errors import InvalidYAMLError
from .models import ProjectFrontMatter


@runtime_checkable
class AppSettings(Protocol):
    """A dataclass with a ``section_key`` class variable."""

    section_key: ClassVar[str]


T = TypeVar("T", bound=AppSettings)

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def snake_to_camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


def camel_to_snake(name: str) -> str:
    return _CAMEL_BOUNDARY.sub("_", name).lower()


def has_settings(front_matter: ProjectFrontMatter, key: str) -> bool:
    return key in front_matter.extra


def settings(front_matter: ProjectFrontMatter, key: str) -> Mapping[str, Any] | None:
    """The raw settings section for ``key``, or ``None``."""
    section = front_matter.extra.get(key)
    if section is None:
        return None
    if not isinstance(section, Mapping):
        raise InvalidYAMLError(
            f"Expected a mapping for settings section {key!r}, "
            f"got {type(section).__name__}"
        )
    return section


def settings_as(front_matter: ProjectFrontMatter, cls: type[T]) -> T | None:
    """Decode the section named by ``cls.section_key`` into ``cls``.

    Keys are matched in both snake_case and camelCase. Unknown keys in the
    section are ignored; a field whose value has the wrong type raises.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} must be a dataclass")
    section = settings(front_matter, cls.section_key)
    if section is None:
        return None

    kwargs: dict[str, Any] = {}
    for field_info in fields(cls):
        if field_info.name == "section_key":
            continue
        for candidate in (field_info.name, snake_to_camel(field_info.name)):
            if candidate in section:
                kwargs[field_info.name] = section[candidate]
                break
        else:
            if field_info.default is MISSING and field_info.default_factory is MISSING:
                raise InvalidYAMLError(
                    f"Settings section {cls.section_key!r} is missing required "
                    f"field {field_info.name!r}"
                )
    return cls(**kwargs)


def with_settings(
    front_matter: ProjectFrontMatter, key: str, section: Mapping[str, Any]
) -> ProjectFrontMatter:
    """Return front matter with ``key`` set to ``section``."""
    extra = dict(front_matter.extra)
    extra[key] = dict(section)
    return front_matter.replace(extra=extra)
