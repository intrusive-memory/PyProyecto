---
type: reference
name: Fixture corpus
description: What each fixture directory is for, and why the corpus is synthetic
updated: 2026-09-19
---

# Fixtures

## `corpus/` — synthetic files with real shapes

These files were derived from real `PROJECT.md` files in production podcast
projects. **The structure is real; the content is invented.** Titles, authors,
descriptions, character names, voice prompts, biographies, episode summaries,
and episode filenames were all replaced. What survives is exactly what the
parser cares about: which keys appear, how they nest, what types the values
have, which scalars were quoted, and where comments sit.

This repository is public and the source files are unreleased creative work, so
a verbatim copy cannot be committed. `test_fixture_hygiene.py` enforces that,
and also asserts the corpus still covers every shape the parser has to handle.

Filenames describe the shape each one covers, for example:

| File | Shape |
|---|---|
| `v3-season-cast-comment-in-block.md` | v3 `season:`, plus a comment inside the `cast:` block — the ruamel deepcopy hazard |
| `episodes-index-intro-outro.md` | `episodes:` with no `season:`, an unknown `episodes_index` key, intro/outro |
| `overview-languages-shorthand.md` | `type: overview` with a shorthand `languages: [es, fr]` list |
| `schema-v4-with-cast.md` | an explicit `schemaVersion: 4` with a legacy cast block |

To add a shape: copy the real file, replace its content, keep its structure, and
name it for what it covers.

`swiftproyecto-fixture.md` comes from SwiftProyecto's own public test suite;
its home-directory paths are rewritten to `/Users/example/`.

## `doc-examples/` — verbatim from SwiftProyecto's docs

Eleven worked examples extracted from `Docs/EXAMPLE_PROJECT_v4.md` and
`Docs/PROJECT_MD_REFERENCE_v4.md`. They are already public, and they are the
only non-synthetic coverage of the master/variant and multi-season shapes.

## `adversarial/` — files that must fail, or parse in one specific way

The Norway problem, an unquoted numeric `model`, a stringy episode count, CRLF,
a BOM, `---` inside the body, content before the front matter, dates without a
timezone, `schemaVersion: 99`, nested unknown keys, no front matter at all, and
a reserved-indicator `author:` value.
