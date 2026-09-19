"""Turning a directory of composition files into a PROJECT.md."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pyproyecto import (
    audit_layout,
    parse_file,
    scaffold_project,
    scan_directory,
    write_document,
)


def _files(root, *relatives):
    for relative in relatives:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("INT. ROOM - DAY\n")


def test_scan_finds_a_flat_directory(tmp_path):
    _files(tmp_path, "one.fountain", "two.fountain")
    scan = scan_directory(tmp_path)
    assert scan.episodes_dir == tmp_path
    assert scan.relative_episodes_dir == "."
    assert scan.episode_count == 2
    assert scan.extensions == (".fountain",)
    assert not scan.is_multi_season


def test_scan_prefers_an_episodes_subdirectory(tmp_path):
    _files(tmp_path, "episodes/one.fountain", "episodes/two.fountain")
    scan = scan_directory(tmp_path)
    assert scan.relative_episodes_dir == "episodes"
    assert scan.episode_count == 2


def test_scan_detects_season_directories(tmp_path):
    _files(
        tmp_path,
        "episodes/season-1/a.fountain",
        "episodes/season-1/b.fountain",
        "episodes/season-2/c.fountain",
    )
    scan = scan_directory(tmp_path)
    assert scan.is_multi_season
    assert [(s.number, s.episode_count) for s in scan.seasons] == [(1, 2), (2, 1)]


@pytest.mark.parametrize("name", ["season-1", "season_1", "Season 1", "s1", "s01"])
def test_scan_recognizes_season_directory_spellings(tmp_path, name):
    _files(tmp_path, f"{name}/a.fountain")
    scan = scan_directory(tmp_path)
    assert [s.number for s in scan.seasons] == [1]


def test_scan_reports_an_existing_project_file(tmp_path):
    _files(tmp_path, "a.fountain")
    assert scan_directory(tmp_path).existing_project is None
    (tmp_path / "PROJECT.md").write_text("---\ntype: project\n---\n")
    assert scan_directory(tmp_path).existing_project == tmp_path / "PROJECT.md"


def test_scan_ignores_generated_and_hidden_directories(tmp_path):
    _files(tmp_path, "episodes/a.fountain", "audio/notes.md", ".git/config.md")
    scan = scan_directory(tmp_path)
    assert [p.name for p in scan.files] == ["a.fountain"]


def test_scan_rejects_a_path_that_is_not_a_directory(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x")
    with pytest.raises(NotADirectoryError):
        scan_directory(target)


# -- scaffolding ----------------------------------------------------------


def test_scaffold_a_flat_project(tmp_path):
    _files(tmp_path, "one.fountain", "two.fountain")
    doc = scaffold_project(
        tmp_path, author="A. Author", created=datetime(2026, 9, 19, tzinfo=UTC)
    )
    fm = doc.front_matter
    assert fm.type == "project"
    assert fm.author == "A. Author"
    assert fm.episodes_dir == "."
    assert fm.file_pattern.patterns == ("*.fountain",)
    assert fm.seasons[0].episodes == 2
    assert "schemaVersion: 5" in doc.to_text()


def test_scaffold_titles_from_the_directory_name(tmp_path):
    project = tmp_path / "the-long-tide"
    project.mkdir()
    _files(project, "a.fountain")
    doc = scaffold_project(project, author="A. Author")
    assert doc.front_matter.title == "The Long Tide"


def test_scaffold_covers_every_extension_present(tmp_path):
    _files(tmp_path, "a.fountain", "b.highland", "c.fountain")
    doc = scaffold_project(tmp_path, author="A. Author")
    patterns = doc.front_matter.file_pattern.patterns
    assert set(patterns) == {"*.fountain", "*.highland"}
    assert patterns[0] == "*.fountain"  # most common first


def test_scaffold_builds_a_seasons_array(tmp_path):
    _files(
        tmp_path,
        "episodes/season-1/a.fountain",
        "episodes/season-2/b.fountain",
        "episodes/season-2/c.fountain",
    )
    doc = scaffold_project(tmp_path, author="A. Author")
    seasons = doc.front_matter.seasons
    assert [(s.number, s.episodes, s.episodes_dir) for s in seasons] == [
        (1, 1, "episodes/season-1"),
        (2, 2, "episodes/season-2"),
    ]


def test_scaffold_handles_an_empty_directory(tmp_path):
    doc = scaffold_project(tmp_path, author="A. Author")
    assert doc.front_matter.seasons is None
    assert doc.front_matter.file_pattern.patterns == ("*.fountain",)


def test_scaffolded_project_audits_clean_end_to_end(tmp_path):
    """The whole adoption path: a folder in, a truthful PROJECT.md out."""
    _files(
        tmp_path,
        "episodes/chapter-1.fountain",
        "episodes/chapter-2.fountain",
        "episodes/chapter-10.fountain",
    )

    doc = scaffold_project(
        tmp_path,
        author="A. Author",
        title="Adopted",
        description="A project that did not have a PROJECT.md this morning.",
    )
    backup = write_document(doc, tmp_path / "PROJECT.md")
    assert backup is None  # nothing was there to rotate

    reloaded = parse_file(tmp_path / "PROJECT.md")
    audit = audit_layout(reloaded)
    assert audit.is_clean, (audit.errors, audit.warnings)
    assert [p.name for p in audit.layout.episode_files] == [
        "chapter-1.fountain",
        "chapter-2.fountain",
        "chapter-10.fountain",
    ]


def test_rescaffolding_rotates_the_existing_project_file(tmp_path):
    _files(tmp_path, "a.fountain")
    first = scaffold_project(tmp_path, author="A. Author", title="First")
    write_document(first, tmp_path / "PROJECT.md")

    second = scaffold_project(tmp_path, author="A. Author", title="Second")
    backup = write_document(second, tmp_path / "PROJECT.md")

    assert backup == tmp_path / "PROJECT.1.md"
    assert "First" in backup.read_text()
    assert parse_file(tmp_path / "PROJECT.md").front_matter.title == "Second"
