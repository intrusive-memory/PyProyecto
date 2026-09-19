from __future__ import annotations

from pyproyecto import parse, parse_file, validate
from pyproyecto.validator import LEGACY_CAST_WARNING


def _fm(extra_yaml: str = "", **overrides: str) -> str:
    fields = {
        "type": "project",
        "title": "X",
        "author": "Y",
        "created": "2025-01-25T00:00:00Z",
    }
    fields.update(overrides)
    body = "".join(f"{k}: {v}\n" for k, v in fields.items())
    return f"---\n{body}{extra_yaml}---\n"


def test_valid_document_has_no_errors():
    assert validate(parse(_fm())).is_valid


def test_empty_title_and_author_are_errors():
    result = validate(parse(_fm(title='""', author='""')))
    assert "Missing or empty title field" in result.errors
    assert "Missing or empty author field" in result.errors


def test_invalid_type_message_matches_swift():
    result = validate(parse(_fm(type="episode")))
    assert 'Invalid type "episode" — must be "project" or "overview"' in result.errors


def test_duplicate_season_numbers():
    yaml = (
        "schemaVersion: 5\n"
        "seasons:\n"
        "  - number: 1\n    episodes: 3\n"
        "  - number: 1\n    episodes: 4\n"
    )
    result = validate(parse(_fm(yaml)))
    assert "Duplicate season numbers: 1" in result.errors


def test_non_positive_episode_count():
    yaml = "schemaVersion: 5\nseasons:\n  - number: 1\n    episodes: 0\n"
    result = validate(parse(_fm(yaml)))
    assert "Season 1 must have episodes > 0, got 0" in result.errors


def test_non_positive_season_number():
    yaml = "schemaVersion: 5\nseasons:\n  - number: 0\n    episodes: 2\n"
    result = validate(parse(_fm(yaml)))
    assert "Season number must be positive, got 0" in result.errors


def test_duplicate_language_codes():
    yaml = (
        "schemaVersion: 5\n"
        "languages:\n"
        "  - code: en\n    name: English\n"
        "  - code: en\n    name: English (US)\n"
    )
    result = validate(parse(_fm(yaml)))
    assert "Duplicate language codes: en" in result.errors


def test_overview_warnings():
    yaml = "schemaVersion: 5\nprojectType: overview\nepisodesDir: episodes\n"
    result = validate(parse(_fm(yaml)))
    assert "Overview files should define a 'variants' array" in result.warnings
    assert (
        "Overview files should not define 'episodesDir' — "
        "that belongs in variants or projects" in result.warnings
    )


def test_v3_warnings_use_the_legacy_rules():
    result = validate(parse(_fm(season="-1", episodes="-3")))
    assert result.metadata.schema_version == 3
    assert "Season number should be positive: -1" in result.warnings


def test_legacy_cast_warning_is_verbatim():
    yaml = "cast:\n  - character: NARRATOR\n"
    result = validate(parse(_fm(yaml)))
    assert LEGACY_CAST_WARNING in result.warnings


def test_metadata_classifies_masters():
    yaml = (
        "schemaVersion: 5\nprojectType: overview\n"
        "variants:\n  - season: 1\n    language: en\n    path: a/PROJECT.md\n"
    )
    result = validate(parse(_fm(yaml)))
    assert result.metadata.file_type == "master"
    assert result.metadata.variant_count == 1


def test_extra_warnings_stay_out_of_the_swift_comparable_list(adversarial):
    leading = validate(parse_file(adversarial / "leading-content.md"))
    assert leading.warnings == ()
    assert any("before the opening" in w for w in leading.extra_warnings)

    future = validate(parse_file(adversarial / "future-schema.md"))
    assert any("Unknown schemaVersion 99" in w for w in future.extra_warnings)
