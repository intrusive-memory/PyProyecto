"""Every real PROJECT.md in the corpus must parse, and survive a round trip.

The corpus is a copy of the files under ~/Projects/podcasts plus
SwiftProyecto's own test fixture, so this is the test that catches a change
that would break files people actually have on disk.
"""

from __future__ import annotations

import pytest

from pyproyecto import parse, parse_file, validate
from tests.conftest import corpus_files


@pytest.mark.parametrize("path", corpus_files(), ids=lambda p: p.stem)
def test_corpus_file_parses(path):
    doc = parse_file(path)
    assert doc.front_matter.title
    assert doc.front_matter.author


@pytest.mark.parametrize("path", corpus_files(), ids=lambda p: p.stem)
def test_corpus_file_round_trips_unchanged(path):
    doc = parse_file(path)
    assert doc.to_text() == path.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("path", corpus_files(), ids=lambda p: p.stem)
def test_corpus_file_survives_an_edit_without_losing_keys(path):
    original = parse_file(path)
    edited = original.with_updates({"genre": original.front_matter.genre or "Test"})
    reparsed = parse(edited.to_text())

    assert set(original.data) <= set(reparsed.data)
    assert reparsed.front_matter.title == original.front_matter.title
    assert (
        reparsed.front_matter.legacy_cast_character_names
        == original.front_matter.legacy_cast_character_names
    )
    assert reparsed.body == original.body


@pytest.mark.parametrize("path", corpus_files(), ids=lambda p: p.stem)
def test_corpus_file_validates_without_errors(path):
    result = validate(parse_file(path))
    assert result.errors == ()


def test_shorthand_language_list_is_read_and_warned_about():
    """A real-world shape Swift cannot read (defect D3); we read it and warn."""
    doc = parse_file(
        next(p for p in corpus_files() if p.stem == "overview-languages-shorthand")
    )
    assert [lang.code for lang in doc.front_matter.languages] == [
        "es",
        "fr",
        "it",
        "pt",
        "de",
    ]
    assert any(w.swift_defect == "D3" for w in doc.warnings)


def test_episodes_without_a_season_keeps_its_count():
    """`episodes:` with no `season:`; Swift discards it (defect D2)."""
    doc = parse_file(
        next(p for p in corpus_files() if p.stem == "episodes-index-intro-outro")
    )
    assert doc.front_matter.episodes == 72
    assert any(w.swift_defect == "D2" for w in doc.warnings)


def test_reserved_indicator_is_a_clear_error(adversarial):
    """A real project file has an `author:` value starting with `@`.

    `@` is a reserved indicator in YAML, so a plain scalar cannot start with
    it. That file is malformed rather than merely unusual, and the error has to
    say where.
    """
    from pyproyecto import InvalidYAMLError, parse_file

    with pytest.raises(InvalidYAMLError) as excinfo:
        parse_file(adversarial / "reserved-indicator-author.md")
    assert excinfo.value.line == 3
    assert "@" in str(excinfo.value)


def test_doc_example_master_file_classifies_as_a_master(doc_examples):
    """The only master/variant coverage that is not synthetic."""
    from pyproyecto import is_master_file, validate

    doc = parse_file(doc_examples / "example-03.md")
    assert is_master_file(doc.front_matter)
    assert len(doc.front_matter.variants) == 3
    assert validate(doc).metadata.file_type == "master"
