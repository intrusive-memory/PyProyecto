"""Variant resolution, discovery, episode templates, and app settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

import pytest

from pyproyecto import (
    FilePattern,
    ProjectFrontMatter,
    SeasonDefinition,
    TTSConfig,
    VariantReference,
    VariantStatus,
    extract_template_variables,
    find_project_md,
    find_variants,
    has_settings,
    is_master_file,
    is_single_project_file,
    is_variant_file,
    load_variant,
    parse,
    resolve_episode_path,
    resolve_variant,
    settings,
    settings_as,
    validate_template,
    with_settings,
)

CREATED = datetime(2025, 1, 25, tzinfo=UTC)


def _master() -> ProjectFrontMatter:
    return ProjectFrontMatter(
        type="overview",
        title="Master",
        author="Tom Stovall",
        created=CREATED,
        description="master description",
        genre="Documentary",
        tags=("a", "b"),
        episodes_dir="episodes",
        audio_dir="audio",
        export_format="m4a",
        intro_file="master-intro.md",
        tts=TTSConfig(provider_id="apple"),
        project_type="overview",
        seasons=(
            SeasonDefinition(
                number=1,
                episodes=10,
                description="season description",
                episodes_dir="episodes/season-1",
                file_pattern=FilePattern(("*.fountain",), True),
                intro_file="season-intro.md",
                tts=TTSConfig(provider_id="voxalta"),
            ),
        ),
    )


# -- variant resolution ---------------------------------------------------


def test_variant_inherits_identity_from_master():
    variant = ProjectFrontMatter(
        type="project", title="Variant", author="Someone", created=CREATED
    )
    resolved = resolve_variant(variant, _master(), season=1)
    assert resolved.title == "Master"
    assert resolved.author == "Tom Stovall"
    assert resolved.created == CREATED
    assert resolved.type == "project"


def test_season_overrides_master_but_variant_wins():
    variant = ProjectFrontMatter(
        type="project",
        title="V",
        author="A",
        created=CREATED,
        intro_file="variant-intro.md",
    )
    resolved = resolve_variant(variant, _master(), season=1)
    assert resolved.intro_file == "variant-intro.md"
    assert resolved.episodes_dir == "episodes/season-1"
    assert resolved.description == "season description"
    assert resolved.tts.provider_id == "voxalta"


def test_empty_tags_fall_back_to_master():
    variant = ProjectFrontMatter(
        type="project", title="V", author="A", created=CREATED, tags=()
    )
    assert resolve_variant(variant, _master(), season=1).tags == ("a", "b")


# -- discovery ------------------------------------------------------------


def test_find_project_md_prefers_the_parent_of_an_episodes_dir(tmp_path, minimal):
    (tmp_path / "episodes").mkdir()
    (tmp_path / "PROJECT.md").write_text(minimal)
    (tmp_path / "episodes" / "ep1.fountain").write_text("INT. ROOM")
    found = find_project_md(tmp_path / "episodes" / "ep1.fountain")
    assert found == tmp_path / "PROJECT.md"


def test_find_project_md_checks_the_directory_then_its_parent(tmp_path, minimal):
    nested = tmp_path / "season-1"
    nested.mkdir()
    (tmp_path / "PROJECT.md").write_text(minimal)
    assert find_project_md(nested) == tmp_path / "PROJECT.md"


def test_find_project_md_returns_none_when_absent(tmp_path):
    assert find_project_md(tmp_path) is None


def test_file_classification():
    master = _master()
    assert is_master_file(master)
    assert not is_single_project_file(master)

    variant = ProjectFrontMatter(
        type="project",
        title="V",
        author="A",
        created=CREATED,
        seasons=(SeasonDefinition(number=1, episodes=3),),
        languages=(),
        project_type="project",
    )
    assert not is_variant_file(variant)  # no languages
    assert is_single_project_file(variant)


def test_load_and_resolve_variants_from_disk(tmp_path):
    (tmp_path / "s1").mkdir()
    (tmp_path / "PROJECT.md").write_text(
        "---\ntype: overview\ntitle: Master\nauthor: Tom\n"
        "created: 2025-01-25T00:00:00Z\nschemaVersion: 5\nprojectType: overview\n"
        "genre: Documentary\n"
        "seasons:\n  - number: 1\n    episodes: 3\n    episodesDir: s1\n"
        "variants:\n  - season: 1\n    language: es\n    path: s1/PROJECT_es.md\n"
        "    status: published\n---\n"
    )
    (tmp_path / "s1" / "PROJECT_es.md").write_text(
        "---\ntype: project\ntitle: Spanish\nauthor: Someone\n"
        "created: 2026-01-01T00:00:00Z\nschemaVersion: 5\n---\n"
    )

    reference = VariantReference(
        season=1,
        language="es",
        path="s1/PROJECT_es.md",
        status=VariantStatus.PUBLISHED,
    )
    resolved = load_variant(reference, tmp_path / "PROJECT.md")
    assert resolved.title == "Master"
    assert resolved.genre == "Documentary"
    assert resolved.episodes_dir == "s1"

    assert len(find_variants(tmp_path / "PROJECT.md")) == 1


# -- episode templates ----------------------------------------------------


def test_resolve_episode_path_uses_angle_bracket_variables():
    resolved = resolve_episode_path(
        "episodes/<language>/season-<season>/ep-<episode>.<ext>",
        language="es",
        season=2,
        episode=7,
        ext="fountain",
    )
    assert resolved == "episodes/es/season-2/ep-7.fountain"


def test_extract_and_validate_template_variables():
    template = "<season>/<episode>.<ext>"
    assert extract_template_variables(template) == ("season", "episode", "ext")
    assert validate_template(template).is_valid


def test_unknown_template_variable_is_invalid():
    """Swift always reports valid here (defect D9)."""
    result = validate_template("episodes/<number>.<ext>")
    assert not result.is_valid
    assert result.invalid_variables == ("number",)


# -- app settings ---------------------------------------------------------


@dataclass(frozen=True)
class MyAppSettings:
    section_key: ClassVar[str] = "myapp"
    theme: str | None = None
    auto_save: bool | None = None


def test_settings_round_trip(minimal):
    doc = parse(
        minimal.replace("---\n", "---\nmyapp:\n  theme: dark\n  autoSave: true\n", 1)
    )
    fm = doc.front_matter
    assert has_settings(fm, "myapp")
    assert settings(fm, "myapp")["theme"] == "dark"

    typed = settings_as(fm, MyAppSettings)
    assert typed == MyAppSettings(theme="dark", auto_save=True)


def test_settings_absent_returns_none(minimal):
    fm = parse(minimal).front_matter
    assert settings(fm, "myapp") is None
    assert settings_as(fm, MyAppSettings) is None


def test_with_settings_adds_a_section(minimal):
    fm = with_settings(parse(minimal).front_matter, "myapp", {"theme": "light"})
    assert settings_as(fm, MyAppSettings).theme == "light"


def test_settings_requires_a_dataclass(minimal):
    with pytest.raises(TypeError):
        settings_as(parse(minimal).front_matter, str)  # type: ignore[type-var]
