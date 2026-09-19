from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
CORPUS = FIXTURES / "corpus"
ADVERSARIAL = FIXTURES / "adversarial"
DOC_EXAMPLES = FIXTURES / "doc-examples"

MINIMAL = """---
type: project
title: Minimal
author: Tom Stovall
created: 2025-01-25T00:00:00Z
---
"""


def corpus_files() -> list[Path]:
    """Real PROJECT.md files, plus the worked examples from SwiftProyecto's docs.

    The doc examples are extracted verbatim from `EXAMPLE_PROJECT_v4.md` and
    `PROJECT_MD_REFERENCE_v4.md`; they are the only coverage of the
    master/variant and multi-season shapes that no real project uses yet.
    """
    return sorted(CORPUS.glob("*.md")) + sorted(DOC_EXAMPLES.glob("*.md"))


@pytest.fixture
def minimal() -> str:
    return MINIMAL


@pytest.fixture
def adversarial() -> Path:
    return ADVERSARIAL


@pytest.fixture
def doc_examples() -> Path:
    return DOC_EXAMPLES
