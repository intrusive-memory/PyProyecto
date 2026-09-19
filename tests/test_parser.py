from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyproyecto import (
    FilePattern,
    InvalidDateError,
    InvalidYAMLError,
    MissingRequiredFieldError,
    NoFrontMatterError,
    parse,
    parse_file,
)


def test_minimal_document(minimal):
    doc = parse(minimal)
    fm = doc.front_matter
    assert fm.type == "project"
    assert fm.title == "Minimal"
    assert fm.author == "Tom Stovall"
    assert fm.created == datetime(2025, 1, 25, tzinfo=UTC)
    assert doc.body == ""


def test_body_is_everything_after_the_closing_delimiter(minimal):
    doc = parse(minimal + "\n# Title\n\nSome prose.\n")
    assert doc.body == "# Title\n\nSome prose."


def test_horizontal_rule_in_body_does_not_confuse_the_split(adversarial):
    doc = parse_file(adversarial / "body-hr.md")
    assert doc.front_matter.title == "Body rule"
    assert doc.body.endswith("After a horizontal rule.")
    assert "---" in doc.body


def test_missing_front_matter(adversarial):
    with pytest.raises(NoFrontMatterError):
        parse_file(adversarial / "no-front-matter.md")


def test_bom_is_tolerated(adversarial):
    assert parse_file(adversarial / "bom.md").front_matter.title == "BOM"


def test_crlf_is_tolerated(adversarial):
    doc = parse_file(adversarial / "crlf.md")
    assert doc.front_matter.title == "CRLF"
    assert doc.body.strip() == "Body line."


def test_leading_content_is_parsed_and_recorded(adversarial):
    doc = parse_file(adversarial / "leading-content.md")
    assert doc.front_matter.title == "Leading"
    assert doc.leading_text.startswith("Leading prose.")


def test_missing_required_field_names_the_field():
    with pytest.raises(MissingRequiredFieldError) as excinfo:
        parse("---\ntype: project\ntitle: X\n---\n")
    assert excinfo.value.field == "author"


def test_missing_nested_required_field_uses_a_dotted_path():
    with pytest.raises(MissingRequiredFieldError) as excinfo:
        parse(
            "---\ntype: project\ntitle: X\nauthor: Y\n"
            "created: 2025-01-25T00:00:00Z\n"
            "seasons:\n  - number: 1\n---\n"
        )
    assert excinfo.value.field == "seasons[0].episodes"


def test_strict_types_reject_a_stringy_episode_count(adversarial):
    with pytest.raises(InvalidYAMLError) as excinfo:
        parse_file(adversarial / "string-episodes.md")
    assert "seasons[0].episodes" in str(excinfo.value)


@pytest.mark.parametrize("name", ["date-only.md", "naive-date.md"])
def test_dates_require_an_explicit_timezone(adversarial, name):
    with pytest.raises(InvalidDateError):
        parse_file(adversarial / name)


def test_offset_dates_normalize_to_utc():
    doc = parse(
        "---\ntype: project\ntitle: X\nauthor: Y\n"
        "created: 2025-01-25T02:00:00+02:00\n---\n"
    )
    assert doc.front_matter.created == datetime(2025, 1, 25, tzinfo=UTC)


def test_file_pattern_single_and_list(minimal):
    single = parse(minimal.replace("---\n", '---\nfilePattern: "*.fountain"\n', 1))
    assert single.front_matter.file_pattern == FilePattern(("*.fountain",), True)
    assert single.front_matter.resolved_file_patterns == ("*.fountain",)

    multi = parse(
        minimal.replace("---\n", '---\nfilePattern: ["*.fountain", "*.fdx"]\n', 1)
    )
    assert multi.front_matter.file_pattern.is_single is False
    assert multi.front_matter.resolved_file_patterns == ("*.fountain", "*.fdx")


def test_defaults_match_swift(minimal):
    fm = parse(minimal).front_matter
    assert fm.resolved_episodes_dir == "episodes"
    assert fm.resolved_audio_dir == "audio"
    assert fm.resolved_file_patterns == ("*.fountain",)
    assert fm.resolved_export_format == "m4a"


def test_v3_season_and_episodes_migrate_into_seasons():
    doc = parse(
        "---\ntype: project\ntitle: X\nauthor: Y\n"
        "created: 2025-01-25T00:00:00Z\nseason: 2\nepisodes: 365\n---\n"
    )
    fm = doc.front_matter
    assert fm.seasons[0].number == 2
    assert fm.seasons[0].episodes == 365
    assert fm.season == 2
    assert fm.episodes == 365
    assert fm.is_legacy_v3_format
    assert fm.detected_schema_version == 3
    # The legacy keys are known keys, so they never land in `extra`.
    assert "season" not in fm.extra


def test_unknown_top_level_keys_are_preserved_in_order(minimal):
    doc = parse(
        minimal.replace("---\n", "---\nepisodes_index: index.json\nzeta: 1\n", 1)
    )
    assert doc.front_matter.extra["episodes_index"] == "index.json"
    assert list(doc.front_matter.extra) == ["episodes_index", "zeta"]


def test_unknown_nested_keys_are_preserved(adversarial):
    """Swift drops these (defect D4); we keep them."""
    fm = parse_file(adversarial / "nested-extras.md").front_matter
    season = fm.seasons[0]
    assert season.extra["cast"][0]["character"] == "NARRATOR"
    assert season.tts.extra["provider"] == "apple"
    assert season.tts.model == "1.7b"


def test_legacy_cast_is_visible_but_not_modelled():
    doc = parse(
        "---\ntype: project\ntitle: X\nauthor: Y\n"
        "created: 2025-01-25T00:00:00Z\n"
        "cast:\n  - character: NARRATOR\n  - character: GUEST\n---\n"
    )
    fm = doc.front_matter
    assert fm.has_legacy_cast_key
    assert fm.legacy_cast_character_names == ("NARRATOR", "GUEST")


def test_quoted_values_become_plain_strings():
    """ruamel's quoted-string subclasses break pathlib; they must not leak."""
    doc = parse(
        "---\ntype: project\ntitle: X\nauthor: Y\n"
        "created: 2025-01-25T00:00:00Z\n"
        'episodesDir: "episodes"\n---\n'
    )
    episodes_dir = doc.front_matter.episodes_dir
    assert type(episodes_dir) is str
    assert (Path("/tmp") / episodes_dir).name == "episodes"
