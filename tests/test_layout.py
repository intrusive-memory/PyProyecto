"""Resolving a declared layout against the files that are actually there."""

from __future__ import annotations

import pytest

from pyproyecto import (
    audit_layout,
    episode_files,
    parse_file,
    resolve_layout,
    write_text,
)

FLAT = """---
type: project
title: Flat
author: A. Author
created: 2025-01-25T00:00:00Z
episodesDir: episodes
filePattern: "*.fountain"
---
"""

MULTI_SEASON = """---
type: project
title: Seasons
author: A. Author
created: 2025-01-25T00:00:00Z
schemaVersion: 5
episodesDir: episodes
filePattern: "*.fountain"
seasons:
  - number: 1
    episodes: 2
    episodesDir: episodes/season-1
  - number: 2
    episodes: 1
    episodesDir: episodes/season-2
    filePattern: "*.highland"
---
"""


def _project(tmp_path, front_matter, files, root_files=()):
    (tmp_path / "PROJECT.md").write_text(front_matter)
    for relative in files:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("INT. ROOM - DAY\n")
    for relative in root_files:
        (tmp_path / relative).write_text("x")
    return parse_file(tmp_path / "PROJECT.md")


def test_episode_files_are_found_in_natural_order(tmp_path):
    doc = _project(
        tmp_path,
        FLAT,
        [
            "episodes/chapter-10.fountain",
            "episodes/chapter-2.fountain",
            "episodes/chapter-1.fountain",
        ],
    )
    names = [p.name for p in episode_files(doc)]
    assert names == ["chapter-1.fountain", "chapter-2.fountain", "chapter-10.fountain"]


def test_layout_resolves_directories_against_the_project_root(tmp_path):
    doc = _project(tmp_path, FLAT, ["episodes/a.fountain"])
    layout = resolve_layout(doc)
    assert layout.root == tmp_path
    assert layout.episodes_dir == tmp_path / "episodes"
    assert layout.audio_dir == tmp_path / "audio"
    assert layout.episode_count == 1
    assert layout.relative_episode_files()[0].as_posix() == "episodes/a.fountain"


def test_non_matching_extensions_are_ignored(tmp_path):
    doc = _project(tmp_path, FLAT, ["episodes/a.fountain", "episodes/notes.md"])
    assert [p.name for p in episode_files(doc)] == ["a.fountain"]


def test_season_overrides_directory_and_pattern(tmp_path):
    doc = _project(
        tmp_path,
        MULTI_SEASON,
        [
            "episodes/season-1/one.fountain",
            "episodes/season-1/two.fountain",
            "episodes/season-2/three.highland",
        ],
    )
    season_one = resolve_layout(doc, season=1)
    assert season_one.episodes_dir == tmp_path / "episodes" / "season-1"
    assert season_one.episode_count == 2

    season_two = resolve_layout(doc, season=2)
    assert season_two.patterns == ("*.highland",)
    assert [p.name for p in season_two.episode_files] == ["three.highland"]


def test_explicit_file_list_reports_what_is_missing(tmp_path):
    front = FLAT.replace(
        'filePattern: "*.fountain"',
        'filePattern: ["intro.fountain", "missing.fountain"]',
    )
    doc = _project(tmp_path, front, ["episodes/intro.fountain"])
    layout = resolve_layout(doc)
    assert [p.name for p in layout.episode_files] == ["intro.fountain"]
    assert [p.name for p in layout.missing_files] == ["missing.fountain"]


def test_layout_needs_a_root_when_the_document_has_no_path():
    from pyproyecto import parse

    with pytest.raises(ValueError):
        resolve_layout(parse(FLAT))


# -- audit ----------------------------------------------------------------


def test_audit_is_clean_when_the_declaration_matches_disk(tmp_path):
    front = FLAT.replace("created:", "episodes: 2\ncreated:")
    doc = _project(tmp_path, front, ["episodes/a.fountain", "episodes/b.fountain"])
    audit = audit_layout(doc)
    assert audit.is_clean, (audit.errors, audit.warnings)


def test_audit_reports_a_missing_episodes_dir(tmp_path):
    (tmp_path / "PROJECT.md").write_text(FLAT)
    audit = audit_layout(parse_file(tmp_path / "PROJECT.md"))
    assert any("episodesDir does not exist" in e for e in audit.errors)


def test_audit_reports_a_count_mismatch(tmp_path):
    front = FLAT.replace("created:", "episodes: 5\ncreated:")
    doc = _project(tmp_path, front, ["episodes/a.fountain"])
    audit = audit_layout(doc)
    assert any("declares 5 episodes but 1 files match" in w for w in audit.warnings)


def test_audit_reports_files_no_pattern_covers(tmp_path):
    doc = _project(tmp_path, FLAT, ["episodes/a.fountain", "episodes/stray.highland"])
    audit = audit_layout(doc)
    assert [p.name for p in audit.unmatched_files] == ["stray.highland"]
    assert any("match no filePattern" in w for w in audit.warnings)


def test_audit_reports_a_missing_intro_file(tmp_path):
    front = FLAT.replace("created:", "introFile: audio/intro.m4a\ncreated:")
    doc = _project(tmp_path, front, ["episodes/a.fountain"])
    audit = audit_layout(doc)
    assert any("introFile does not exist" in w for w in audit.warnings)


def test_audit_accepts_an_intro_file_relative_to_the_project_root(tmp_path):
    """Project-resolved, not episodesDir-resolved (defect D7)."""
    front = FLAT.replace("created:", "introFile: audio/intro.m4a\ncreated:")
    doc = _project(tmp_path, front, ["episodes/a.fountain"])
    write_text(tmp_path / "audio" / "intro.m4a", "audio")
    audit = audit_layout(doc)
    assert not any("introFile" in w for w in audit.warnings)
