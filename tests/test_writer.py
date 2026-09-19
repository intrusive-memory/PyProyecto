"""Writes must never destroy the previous version."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pyproyecto import (
    ProjectDocument,
    ProjectFrontMatter,
    list_backups,
    next_backup_path,
    parse,
    parse_file,
    restore_backup,
    write_document,
    write_text,
)


def test_first_write_makes_no_backup(tmp_path, minimal):
    target = tmp_path / "PROJECT.md"
    assert write_text(target, minimal) is None
    assert target.read_text() == minimal
    assert list_backups(target) == []


def test_each_write_rotates_the_previous_file(tmp_path, minimal):
    target = tmp_path / "PROJECT.md"
    write_text(target, minimal)

    first = write_text(target, minimal.replace("Minimal", "Second"))
    assert first == tmp_path / "PROJECT.1.md"
    assert first.read_text() == minimal

    second = write_text(target, minimal.replace("Minimal", "Third"))
    assert second == tmp_path / "PROJECT.2.md"
    assert "Second" in second.read_text()
    assert "Third" in target.read_text()

    assert [p.name for p in list_backups(target)] == ["PROJECT.1.md", "PROJECT.2.md"]


def test_backup_numbers_are_never_reused(tmp_path, minimal):
    target = tmp_path / "PROJECT.md"
    write_text(target, minimal)
    write_text(target, minimal + "\nv2\n")
    write_text(target, minimal + "\nv3\n")

    (tmp_path / "PROJECT.1.md").unlink()
    assert next_backup_path(target) == tmp_path / "PROJECT.3.md"
    assert write_text(target, minimal + "\nv4\n") == tmp_path / "PROJECT.3.md"


def test_backup_can_be_disabled(tmp_path, minimal):
    target = tmp_path / "PROJECT.md"
    write_text(target, minimal)
    assert write_text(target, "replaced", backup=False) is None
    assert list_backups(target) == []


def test_restore_backup_rotates_the_current_file_too(tmp_path, minimal):
    target = tmp_path / "PROJECT.md"
    write_text(target, minimal)
    write_text(target, minimal.replace("Minimal", "Broken"))

    restore_backup(target)
    assert "Minimal" in target.read_text()
    # The bad version is still recoverable.
    assert any("Broken" in p.read_text() for p in list_backups(target))


def test_failed_write_leaves_the_original_in_place(tmp_path, minimal, monkeypatch):
    target = tmp_path / "PROJECT.md"
    write_text(target, minimal)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pyproyecto.writer.os.replace", boom)
    with pytest.raises(OSError):
        write_text(target, "new content")

    assert target.read_text() == minimal
    assert not list(tmp_path.glob(".PROJECT.md.*.tmp"))


def test_unmodified_round_trip_is_byte_identical(tmp_path, minimal):
    target = tmp_path / "PROJECT.md"
    target.write_text(minimal + "\n# Body\n")
    doc = parse_file(target)
    assert doc.to_text() == minimal + "\n# Body\n"
    write_document(doc)
    assert target.read_text() == minimal + "\n# Body\n"


def test_edits_preserve_comments_and_unknown_keys(tmp_path):
    source = """---
type: project
# who made this
title: Commented
author: Tom Stovall
created: 2025-01-25T00:00:00Z
episodes_index: index.json
cast:
  - character: NARRATOR
    voices:
      voxalta: voices/NARRATOR.vox
---

Body text.
"""
    target = tmp_path / "PROJECT.md"
    target.write_text(source)

    doc = parse_file(target).with_updates({"genre": "Documentary"})
    write_document(doc)

    written = target.read_text()
    assert "# who made this" in written
    assert "episodes_index: index.json" in written
    assert "voices/NARRATOR.vox" in written
    assert "genre: Documentary" in written
    assert parse(written).front_matter.genre == "Documentary"
    assert parse(written).body == "Body text."


def test_full_reemit_keeps_nested_season_keys(tmp_path, adversarial):
    """Swift's writer drops these (defect D1); a re-emit here must not."""
    doc = parse_file(adversarial / "nested-extras.md")
    rewritten = parse(doc.with_front_matter(doc.front_matter).to_text())
    season = rewritten.front_matter.seasons[0]
    assert season.file_pattern.patterns == ("*.fountain",)
    assert season.intro_file == "intro.md"
    assert season.outro_file == "outro.md"
    assert season.tts.model == "1.7b"
    assert season.tts.extra["provider"] == "apple"
    assert season.extra["cast"][0]["character"] == "NARRATOR"


def test_new_document_is_stamped_with_the_current_schema_version():
    fm = ProjectFrontMatter(
        type="project",
        title="Fresh",
        author="Tom Stovall",
        created=datetime(2026, 9, 19, tzinfo=UTC),
    )
    text = ProjectDocument.new(fm, body="# Fresh").to_text()
    assert "schemaVersion: 5" in text
    assert "created: 2026-09-19T00:00:00Z" in text
    reparsed = parse(text)
    assert reparsed.front_matter.title == "Fresh"
    assert reparsed.body == "# Fresh"


def test_write_document_requires_a_destination(minimal):
    with pytest.raises(ValueError):
        write_document(parse(minimal))
