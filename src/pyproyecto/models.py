"""The PROJECT.md data model.

Field names are snake_case; the YAML keys they map to are camelCase, matching
SwiftProyecto's ``ProjectFrontMatter`` and friends. Decoding is strict in the
same places Swift's ``Codable`` is strict: a string where an int belongs is an
error, not a coercion.

Unknown keys are never dropped. Unknown *top-level* keys land in
:attr:`ProjectFrontMatter.extra`; unknown keys nested inside a known object
(a season-level ``cast:``, an unrecognized ``tts`` key) land in that object's
own ``extra``. Swift discards the nested ones -- defect D4.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar, Final

from .errors import (
    ConformanceWarning,
    InvalidDateError,
    InvalidYAMLError,
    MissingRequiredFieldError,
)

CURRENT_SCHEMA_VERSION: Final = 5
"""The schema version PyProyecto stamps on write (ProjectSchemaVersion.current)."""

LEGACY_SCHEMA_VERSION: Final = 3
"""The version assumed when a document declares none."""

SUPPORTED_SCHEMA_VERSIONS: Final = (3, 4, 5)

DEFAULT_EPISODES_DIR: Final = "episodes"
DEFAULT_AUDIO_DIR: Final = "audio"
DEFAULT_FILE_PATTERNS: Final = ("*.fountain",)
DEFAULT_EXPORT_FORMAT: Final = "m4a"


# --------------------------------------------------------------------------
# Scalar coercion. Every helper takes the dotted path so errors can name it.
# --------------------------------------------------------------------------


def _type_error(path: str, expected: str, value: object) -> InvalidYAMLError:
    actual = type(value).__name__
    return InvalidYAMLError(f"Expected {expected} for {path}, got {actual} ({value!r})")


def _as_str(value: object, path: str) -> str:
    if isinstance(value, str):
        return value
    raise _type_error(path, "a string", value)


def _as_int(value: object, path: str) -> int:
    # bool is an int subclass in Python; YAML `true` is not an episode count.
    if isinstance(value, bool) or not isinstance(value, int):
        raise _type_error(path, "an integer", value)
    return value


def _as_mapping(value: object, path: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise _type_error(path, "a mapping", value)


def _as_sequence(value: object, path: str) -> Sequence[Any]:
    if isinstance(value, (str, Mapping)):
        raise _type_error(path, "a list", value)
    if isinstance(value, Sequence):
        return value
    raise _type_error(path, "a list", value)


def _opt(mapping: Mapping[str, Any], key: str) -> object | None:
    value = mapping.get(key)
    return None if value is None else value


def _opt_str(mapping: Mapping[str, Any], key: str, path: str) -> str | None:
    value = _opt(mapping, key)
    return None if value is None else _as_str(value, f"{path}{key}")


def _opt_int(mapping: Mapping[str, Any], key: str, path: str) -> int | None:
    value = _opt(mapping, key)
    return None if value is None else _as_int(value, f"{path}{key}")


def _require(mapping: Mapping[str, Any], key: str, path: str) -> object:
    if key not in mapping or mapping[key] is None:
        raise MissingRequiredFieldError(f"{path}{key}")
    return mapping[key]


def parse_timestamp(value: object, path: str) -> datetime:
    """Parse an ISO 8601 timestamp, requiring an explicit timezone.

    Date-only values and naive datetimes are rejected (open question 6), which
    matches Swift's ``ISO8601DateFormatter``. The result is normalized to UTC.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            raise InvalidDateError(path, value) from None
    else:
        raise InvalidDateError(path, value)
    if parsed.tzinfo is None:
        raise InvalidDateError(path, value)
    return parsed.astimezone(UTC)


def format_timestamp(value: datetime) -> str:
    """Render a datetime the way Swift's ``ISO8601DateFormatter`` does."""
    return value.astimezone(UTC).replace(microsecond=0, tzinfo=None).isoformat() + "Z"


_KNOWN_NESTED_KEYS: Final = {"extra"}


def _extras(mapping: Mapping[str, Any], known: Sequence[str]) -> dict[str, Any]:
    """Every key of ``mapping`` that is not in ``known``, in document order."""
    known_set = set(known)
    return {k: v for k, v in mapping.items() if k not in known_set}


# --------------------------------------------------------------------------
# Value types
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FilePattern:
    """A glob pattern or explicit file list.

    Remembers whether the source was a bare string or a list so a write can
    put it back the way it was found.
    """

    patterns: tuple[str, ...]
    is_single: bool = False

    @classmethod
    def parse(cls, value: object, path: str) -> FilePattern:
        if isinstance(value, str):
            return cls((value,), is_single=True)
        items = _as_sequence(value, path)
        return cls(
            tuple(_as_str(item, f"{path}[{i}]") for i, item in enumerate(items)),
            is_single=False,
        )

    def to_yaml(self) -> str | list[str]:
        if self.is_single and len(self.patterns) == 1:
            return self.patterns[0]
        return list(self.patterns)

    def __str__(self) -> str:
        if self.is_single and len(self.patterns) == 1:
            return self.patterns[0]
        return "[" + ", ".join(self.patterns) + "]"


@dataclass(frozen=True, slots=True)
class TTSConfig:
    """Text-to-speech configuration.

    These are the key names the Swift *code* uses. ``PROJECT_MD_REFERENCE_v4``
    documents ``provider``/``voiceLanguage``; that doc is stale (defect D5), so
    those arrive as unknown keys in :attr:`extra` rather than being silently
    dropped.
    """

    provider_id: str | None = None
    voice_id: str | None = None
    language_code: str | None = None
    voice_uri: str | None = None
    model: str | None = None
    action_line_voice: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    _YAML_KEYS: ClassVar[tuple[str, ...]] = (
        "providerId",
        "voiceId",
        "languageCode",
        "voiceURI",
        "model",
        "actionLineVoice",
    )

    @classmethod
    def parse(cls, value: object, path: str) -> TTSConfig:
        mapping = _as_mapping(value, path.rstrip("."))
        prefix = f"{path}"
        return cls(
            provider_id=_opt_str(mapping, "providerId", prefix),
            voice_id=_opt_str(mapping, "voiceId", prefix),
            language_code=_opt_str(mapping, "languageCode", prefix),
            voice_uri=_opt_str(mapping, "voiceURI", prefix),
            model=_opt_str(mapping, "model", prefix),
            action_line_voice=_opt_str(mapping, "actionLineVoice", prefix),
            extra=_extras(mapping, cls._YAML_KEYS),
        )

    def to_yaml(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in (
            ("providerId", self.provider_id),
            ("voiceId", self.voice_id),
            ("languageCode", self.language_code),
            ("voiceURI", self.voice_uri),
            ("model", self.model),
            ("actionLineVoice", self.action_line_voice),
        ):
            if value is not None:
                out[key] = value
        out.update(self.extra)
        return out


@dataclass(frozen=True, slots=True)
class SeasonDefinition:
    """One entry of the ``seasons`` array."""

    number: int
    episodes: int
    title: str | None = None
    description: str | None = None
    release_date: datetime | None = None
    episodes_dir: str | None = None
    file_pattern: FilePattern | None = None
    intro_file: str | None = None
    outro_file: str | None = None
    tts: TTSConfig | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    _YAML_KEYS: ClassVar[tuple[str, ...]] = (
        "number",
        "episodes",
        "title",
        "description",
        "releaseDate",
        "episodesDir",
        "filePattern",
        "introFile",
        "outroFile",
        "tts",
    )

    @classmethod
    def parse(cls, value: object, path: str) -> SeasonDefinition:
        mapping = _as_mapping(value, path)
        prefix = f"{path}."
        release = _opt(mapping, "releaseDate")
        pattern = _opt(mapping, "filePattern")
        tts = _opt(mapping, "tts")
        return cls(
            number=_as_int(_require(mapping, "number", prefix), f"{prefix}number"),
            episodes=_as_int(
                _require(mapping, "episodes", prefix), f"{prefix}episodes"
            ),
            title=_opt_str(mapping, "title", prefix),
            description=_opt_str(mapping, "description", prefix),
            release_date=(
                None
                if release is None
                else parse_timestamp(release, f"{prefix}releaseDate")
            ),
            episodes_dir=_opt_str(mapping, "episodesDir", prefix),
            file_pattern=(
                None
                if pattern is None
                else FilePattern.parse(pattern, f"{prefix}filePattern")
            ),
            intro_file=_opt_str(mapping, "introFile", prefix),
            outro_file=_opt_str(mapping, "outroFile", prefix),
            tts=None if tts is None else TTSConfig.parse(tts, f"{prefix}tts."),
            extra=_extras(mapping, cls._YAML_KEYS),
        )

    def to_yaml(self) -> dict[str, Any]:
        out: dict[str, Any] = {"number": self.number}
        if self.title is not None:
            out["title"] = self.title
        if self.description is not None:
            out["description"] = self.description
        out["episodes"] = self.episodes
        if self.release_date is not None:
            out["releaseDate"] = format_timestamp(self.release_date)
        if self.episodes_dir is not None:
            out["episodesDir"] = self.episodes_dir
        if self.file_pattern is not None:
            out["filePattern"] = self.file_pattern.to_yaml()
        if self.intro_file is not None:
            out["introFile"] = self.intro_file
        if self.outro_file is not None:
            out["outroFile"] = self.outro_file
        if self.tts is not None:
            out["tts"] = self.tts.to_yaml()
        out.update(self.extra)
        return out


@dataclass(frozen=True, slots=True)
class LanguageDefinition:
    """One entry of the ``languages`` array."""

    code: str
    name: str
    locale: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    _YAML_KEYS: ClassVar[tuple[str, ...]] = ("code", "name", "locale")

    @classmethod
    def parse(
        cls,
        value: object,
        path: str,
        warnings: list[ConformanceWarning] | None = None,
    ) -> LanguageDefinition:
        # Leniency, per open question 3: `languages: [es, fr]` is a real
        # shorthand (podcasts/lingua-matra) that Swift rejects outright --
        # defect D3.
        if isinstance(value, str):
            if warnings is not None:
                warnings.append(
                    ConformanceWarning(
                        field=path,
                        message=(
                            f"Language {value!r} is a bare string; SwiftProyecto "
                            "requires a mapping with 'code' and 'name'"
                        ),
                        swift_defect="D3",
                    )
                )
            return cls(code=value, name=value)
        mapping = _as_mapping(value, path)
        prefix = f"{path}."
        return cls(
            code=_as_str(_require(mapping, "code", prefix), f"{prefix}code"),
            name=_as_str(_require(mapping, "name", prefix), f"{prefix}name"),
            locale=_opt_str(mapping, "locale", prefix),
            extra=_extras(mapping, cls._YAML_KEYS),
        )

    def to_yaml(self) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "name": self.name}
        if self.locale is not None:
            out["locale"] = self.locale
        out.update(self.extra)
        return out


class VariantStatus(StrEnum):
    """Production status of a variant PROJECT.md."""

    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    DRAFT = "draft"
    OBSOLETE = "obsolete"


@dataclass(frozen=True, slots=True)
class VariantReference:
    """One entry of the ``variants`` array."""

    season: int
    language: str
    path: str
    status: VariantStatus | None = None
    intro_file: str | None = None
    outro_file: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    _YAML_KEYS: ClassVar[tuple[str, ...]] = (
        "season",
        "language",
        "path",
        "status",
        "introFile",
        "outroFile",
    )

    @classmethod
    def parse(cls, value: object, path: str) -> VariantReference:
        mapping = _as_mapping(value, path)
        prefix = f"{path}."
        raw_status = _opt_str(mapping, "status", prefix)
        if raw_status is None:
            status = None
        else:
            try:
                status = VariantStatus(raw_status)
            except ValueError:
                raise InvalidYAMLError(
                    f"Invalid variant status {raw_status!r} at {prefix}status "
                    f"(expected one of {', '.join(s.value for s in VariantStatus)})"
                ) from None
        return cls(
            season=_as_int(_require(mapping, "season", prefix), f"{prefix}season"),
            language=_as_str(
                _require(mapping, "language", prefix), f"{prefix}language"
            ),
            path=_as_str(_require(mapping, "path", prefix), f"{prefix}path"),
            status=status,
            intro_file=_opt_str(mapping, "introFile", prefix),
            outro_file=_opt_str(mapping, "outroFile", prefix),
            extra=_extras(mapping, cls._YAML_KEYS),
        )

    def to_yaml(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "season": self.season,
            "language": self.language,
            "path": self.path,
        }
        if self.status is not None:
            out["status"] = self.status.value
        if self.intro_file is not None:
            out["introFile"] = self.intro_file
        if self.outro_file is not None:
            out["outroFile"] = self.outro_file
        out.update(self.extra)
        return out


# --------------------------------------------------------------------------
# Front matter
# --------------------------------------------------------------------------

KNOWN_TOP_LEVEL_KEYS: Final = (
    "type",
    "title",
    "author",
    "created",
    "updated",
    "description",
    "season",
    "episodes",
    "genre",
    "tags",
    "episodesDir",
    "audioDir",
    "filePattern",
    "exportFormat",
    "introFile",
    "outroFile",
    "preGenerateHook",
    "postGenerateHook",
    "tts",
    "schemaVersion",
    "projectType",
    "seasons",
    "languages",
    "variants",
    "episodePath",
)
"""Mirrors ``ProjectFrontMatter.KnownCodingKeys``; anything else is `extra`."""

CANONICAL_KEY_ORDER: Final = (
    "type",
    "title",
    "author",
    "created",
    "updated",
    "description",
    "genre",
    "tags",
    "schemaVersion",
    "projectType",
    "seasons",
    "languages",
    "variants",
    "episodePath",
    "episodesDir",
    "audioDir",
    "filePattern",
    "exportFormat",
    "introFile",
    "outroFile",
    "preGenerateHook",
    "postGenerateHook",
    "tts",
)
"""Key order for documents built from scratch, following Swift's emitter."""


@dataclass(frozen=True, slots=True)
class ProjectFrontMatter:
    """Parsed PROJECT.md front matter."""

    type: str
    title: str
    author: str
    created: datetime
    updated: datetime | None = None
    description: str | None = None
    genre: str | None = None
    tags: tuple[str, ...] | None = None
    episodes_dir: str | None = None
    audio_dir: str | None = None
    file_pattern: FilePattern | None = None
    export_format: str | None = None
    intro_file: str | None = None
    outro_file: str | None = None
    pre_generate_hook: str | None = None
    post_generate_hook: str | None = None
    tts: TTSConfig | None = None
    schema_version: int | None = None
    project_type: str | None = None
    seasons: tuple[SeasonDefinition, ...] | None = None
    languages: tuple[LanguageDefinition, ...] | None = None
    variants: tuple[VariantReference, ...] | None = None
    episode_path: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    # -- parsing ----------------------------------------------------------

    @classmethod
    def parse(
        cls,
        mapping: Mapping[str, Any],
        warnings: list[ConformanceWarning] | None = None,
    ) -> ProjectFrontMatter:
        """Build front matter from a loaded YAML mapping."""
        if warnings is None:
            warnings = []
        data = _as_mapping(mapping, "<front matter>")

        tags_raw = _opt(data, "tags")
        tags: tuple[str, ...] | None = None
        if tags_raw is not None:
            items = _as_sequence(tags_raw, "tags")
            tags = tuple(_as_str(t, f"tags[{i}]") for i, t in enumerate(items))

        pattern_raw = _opt(data, "filePattern")
        tts_raw = _opt(data, "tts")
        updated_raw = _opt(data, "updated")

        languages_raw = _opt(data, "languages")
        languages: tuple[LanguageDefinition, ...] | None = None
        if languages_raw is not None:
            items = _as_sequence(languages_raw, "languages")
            languages = tuple(
                LanguageDefinition.parse(item, f"languages[{i}]", warnings)
                for i, item in enumerate(items)
            )

        variants_raw = _opt(data, "variants")
        variants: tuple[VariantReference, ...] | None = None
        if variants_raw is not None:
            items = _as_sequence(variants_raw, "variants")
            variants = tuple(
                VariantReference.parse(item, f"variants[{i}]")
                for i, item in enumerate(items)
            )

        seasons = cls._parse_seasons(data, warnings)

        return cls(
            type=_as_str(_require(data, "type", ""), "type"),
            title=_as_str(_require(data, "title", ""), "title"),
            author=_as_str(_require(data, "author", ""), "author"),
            created=parse_timestamp(_require(data, "created", ""), "created"),
            updated=(
                None if updated_raw is None else parse_timestamp(updated_raw, "updated")
            ),
            description=_opt_str(data, "description", ""),
            genre=_opt_str(data, "genre", ""),
            tags=tags,
            episodes_dir=_opt_str(data, "episodesDir", ""),
            audio_dir=_opt_str(data, "audioDir", ""),
            file_pattern=(
                None
                if pattern_raw is None
                else FilePattern.parse(pattern_raw, "filePattern")
            ),
            export_format=_opt_str(data, "exportFormat", ""),
            intro_file=_opt_str(data, "introFile", ""),
            outro_file=_opt_str(data, "outroFile", ""),
            pre_generate_hook=_opt_str(data, "preGenerateHook", ""),
            post_generate_hook=_opt_str(data, "postGenerateHook", ""),
            tts=None if tts_raw is None else TTSConfig.parse(tts_raw, "tts."),
            schema_version=_opt_int(data, "schemaVersion", ""),
            project_type=_opt_str(data, "projectType", ""),
            seasons=seasons,
            languages=languages,
            variants=variants,
            episode_path=_opt_str(data, "episodePath", ""),
            extra=_extras(data, KNOWN_TOP_LEVEL_KEYS),
        )

    @staticmethod
    def _parse_seasons(
        data: Mapping[str, Any], warnings: list[ConformanceWarning]
    ) -> tuple[SeasonDefinition, ...] | None:
        """Seasons, including the v3 ``season:``/``episodes:`` migration."""
        seasons_raw = _opt(data, "seasons")
        if seasons_raw is not None:
            items = _as_sequence(seasons_raw, "seasons")
            return tuple(
                SeasonDefinition.parse(item, f"seasons[{i}]")
                for i, item in enumerate(items)
            )

        legacy_season = _opt_int(data, "season", "")
        legacy_episodes = _opt_int(data, "episodes", "")

        if legacy_season is not None:
            return (
                SeasonDefinition(number=legacy_season, episodes=legacy_episodes or 0),
            )

        if legacy_episodes is not None:
            # Leniency, per open question 3: Swift decodes a bare `episodes:`
            # and then throws it away (defect D2). podcasts/confessions has
            # `episodes: 72` and no season.
            warnings.append(
                ConformanceWarning(
                    field="episodes",
                    message=(
                        f"episodes: {legacy_episodes} has no accompanying season:; "
                        "assuming season 1. SwiftProyecto discards this value"
                    ),
                    swift_defect="D2",
                )
            )
            return (SeasonDefinition(number=1, episodes=legacy_episodes),)

        return None

    # -- serialization ----------------------------------------------------

    def to_yaml(self) -> dict[str, Any]:
        """Render to a plain mapping in :data:`CANONICAL_KEY_ORDER`.

        Every field is emitted, including nested season and variant keys that
        Swift's writer drops (defect D1), so a read-write cycle is lossless.
        """
        out: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "author": self.author,
            "created": format_timestamp(self.created),
        }
        if self.updated is not None:
            out["updated"] = format_timestamp(self.updated)
        if self.description is not None:
            out["description"] = self.description
        if self.genre is not None:
            out["genre"] = self.genre
        if self.tags is not None:
            out["tags"] = list(self.tags)

        out["schemaVersion"] = CURRENT_SCHEMA_VERSION

        if self.project_type is not None:
            out["projectType"] = self.project_type
        if self.seasons:
            out["seasons"] = [s.to_yaml() for s in self.seasons]
        if self.languages:
            out["languages"] = [lang.to_yaml() for lang in self.languages]
        if self.variants:
            out["variants"] = [v.to_yaml() for v in self.variants]
        if self.episode_path is not None:
            out["episodePath"] = self.episode_path
        if self.episodes_dir is not None:
            out["episodesDir"] = self.episodes_dir
        if self.audio_dir is not None:
            out["audioDir"] = self.audio_dir
        if self.file_pattern is not None:
            out["filePattern"] = self.file_pattern.to_yaml()
        if self.export_format is not None:
            out["exportFormat"] = self.export_format
        if self.intro_file is not None:
            out["introFile"] = self.intro_file
        if self.outro_file is not None:
            out["outroFile"] = self.outro_file
        if self.pre_generate_hook is not None:
            out["preGenerateHook"] = self.pre_generate_hook
        if self.post_generate_hook is not None:
            out["postGenerateHook"] = self.post_generate_hook
        if self.tts is not None:
            out["tts"] = self.tts.to_yaml()

        out.update(self.extra)
        return out

    # -- convenience ------------------------------------------------------

    @property
    def season(self) -> int | None:
        """Backward-compatible v3 season number (``seasons[0].number``)."""
        return self.seasons[0].number if self.seasons else None

    @property
    def episodes(self) -> int | None:
        """Backward-compatible v3 episode count (``seasons[0].episodes``)."""
        return self.seasons[0].episodes if self.seasons else None

    @property
    def detected_schema_version(self) -> int:
        return (
            self.schema_version
            if self.schema_version is not None
            else LEGACY_SCHEMA_VERSION
        )

    @property
    def is_legacy_v3_format(self) -> bool:
        return self.schema_version is None

    @property
    def resolved_episodes_dir(self) -> str:
        return self.episodes_dir or DEFAULT_EPISODES_DIR

    @property
    def resolved_audio_dir(self) -> str:
        return self.audio_dir or DEFAULT_AUDIO_DIR

    @property
    def resolved_file_patterns(self) -> tuple[str, ...]:
        return (
            self.file_pattern.patterns
            if self.file_pattern is not None
            else DEFAULT_FILE_PATTERNS
        )

    @property
    def resolved_export_format(self) -> str:
        return self.export_format or DEFAULT_EXPORT_FORMAT

    @property
    def has_tts_config(self) -> bool:
        return self.tts is not None

    @property
    def has_generation_config(self) -> bool:
        return any(
            v is not None
            for v in (
                self.episodes_dir,
                self.audio_dir,
                self.file_pattern,
                self.export_format,
                self.pre_generate_hook,
                self.post_generate_hook,
            )
        )

    # -- legacy cast (read-only; CAST.md belongs to SwiftReparto) ---------

    @property
    def has_legacy_cast_key(self) -> bool:
        return "cast" in self.extra

    @property
    def legacy_cast_character_names(self) -> tuple[str, ...]:
        """``character:`` names in a legacy ``cast:`` block, in order.

        This is the only reading PyProyecto does of a cast block; the rest is
        opaque data preserved verbatim.
        """
        block = self.extra.get("cast")
        if not isinstance(block, Sequence) or isinstance(block, (str, bytes)):
            return ()
        names: list[str] = []
        for member in block:
            if isinstance(member, Mapping):
                name = member.get("character")
                if isinstance(name, str):
                    names.append(name)
        return tuple(names)

    def replace(self, **changes: Any) -> ProjectFrontMatter:
        """Return a copy with ``changes`` applied."""
        return replace(self, **changes)
