"""The fixture corpus must stay synthetic.

The shapes in `tests/fixtures/corpus/` were taken from real projects, but the
content is invented. This repository is public, and the real files carry
unreleased episode summaries, character bios, and voice direction. Copying one
in verbatim would publish it.

If you need a new shape, copy the real file, replace its content, and keep the
structure.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from .conftest import ADVERSARIAL, CORPUS

# Identifiers that only appear in real project files. This is a tripwire for an
# accidental copy, not a security control.
PERSONAL_IDENTIFIERS = (
    "stovak",
    "stovall",
)

# A home directory path with a real username in it. `/Users/example/` is the
# sanitized placeholder and is allowed.
HOME_PATH = re.compile(r"/Users/(?!example/)[^/\s\"']+", re.IGNORECASE)

# `doc-examples/` is exempt: those files are copied verbatim from
# SwiftProyecto's public documentation, where the same names already appear.
# Rewriting them would make them stop being what they claim to be.
FIXTURE_DIRS = (CORPUS, ADVERSARIAL)


def all_fixtures() -> list[pathlib.Path]:
    return sorted(p for d in FIXTURE_DIRS for p in d.glob("*.md"))


@pytest.mark.parametrize("path", all_fixtures(), ids=lambda p: p.stem)
def test_fixture_carries_no_personal_identifiers(path: pathlib.Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    found = [t for t in PERSONAL_IDENTIFIERS if t.lower() in text.lower()]
    found += HOME_PATH.findall(text)
    assert not found, (
        f"{path.name} contains {found}. Fixtures are published; replace the "
        "content and keep only the structure."
    )


def test_corpus_covers_the_shapes_the_parser_has_to_handle() -> None:
    """The synthetic corpus is only worth having if it still covers everything."""
    from pyproyecto import parse_file

    shapes = {
        "legacy_cast": False,
        "v3_season": False,
        "episodes_without_season": False,
        "shorthand_languages": False,
        "schema_v4_declared": False,
        "file_pattern_list": False,
        "intro_outro": False,
        "comment_in_cast_block": False,
        "unknown_top_level_key": False,
        "overview_type": False,
        "non_empty_body": False,
    }

    for path in sorted(CORPUS.glob("*.md")):
        doc = parse_file(path)
        fm = doc.front_matter
        data = doc.data
        front = path.read_text(encoding="utf-8-sig").split("---")[1]

        shapes["legacy_cast"] |= fm.has_legacy_cast_key
        shapes["v3_season"] |= "season" in data
        shapes["episodes_without_season"] |= "episodes" in data and "season" not in data
        shapes["shorthand_languages"] |= isinstance(
            data.get("languages", [None])[0], str
        )
        shapes["schema_v4_declared"] |= data.get("schemaVersion") == 4
        shapes["file_pattern_list"] |= isinstance(data.get("filePattern"), list)
        shapes["intro_outro"] |= fm.intro_file is not None
        shapes["comment_in_cast_block"] |= "#" in front
        shapes["unknown_top_level_key"] |= bool(set(fm.extra) - {"cast"})
        shapes["overview_type"] |= fm.type == "overview"
        shapes["non_empty_body"] |= bool(doc.body)

    missing = [name for name, covered in shapes.items() if not covered]
    assert not missing, f"corpus no longer covers: {missing}"
