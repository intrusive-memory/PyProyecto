---
type: reference
name: AGENTS.md
description: Quick reference for AI agents working with PyProyecto
updated: 2026-09-19
---

# PyProyecto — Agent Quick Reference

Python port of [SwiftProyecto](https://github.com/intrusive-memory/SwiftProyecto)'s
`PROJECT.md` parser, published to PyPI as `pyproyecto`. First package in the
`~/Projects/python` tree.

**What it does**: parses and writes `PROJECT.md` (schema v3/v4/v5), validates it
with SwiftProyecto's exact messages, resolves variants against masters, finds
`PROJECT.md` from a starting path, and resolves episode path templates.

**What it doesn't do**: cast (`CAST.md` belongs to SwiftReparto), LLM project
generation, `proyecto migrate`, UI, audio batch iteration.

Requirements and the settled open questions live in
[REQUIREMENTS.md](REQUIREMENTS.md). Read it before changing behavior.

---

## Pipeline: development → main → tagged release

All work lands on `development`. `main` is the released state. A tag on `main`
is what produces a release.

```
  feature work
       │
       ▼
  development ──PR──▶ main ──tag v<x.y.z>──▶ GitHub release ──▶ PyPI
       │               │                          │              │
    CI: tests      CI: tests +              tests re-run     final action;
    on every       required checks          at the tag;      requires a PyPI
    push/PR        before merge             tag must match   account (see
                                            the version      RELEASING.md)
```

**Rules:**

1. **Never commit to `main`.** It takes pull requests from `development` only.
2. **Never push directly to a protected branch.** Branch protection on `main`
   requires the `Unit tests` and `Lint and type check` checks to pass.
3. **Every merge into `main` runs the unit tests**, across Python 3.11–3.14.
4. **Releases are tagged `v<version>`**, and the tag must match `version` in
   `pyproject.toml`. The release workflow fails the build if they disagree.
5. **Publishing to PyPI is the last action**, and it is deliberately switched
   off until an account and a Trusted Publisher exist. See
   [RELEASING.md](RELEASING.md).

**Cutting a release:**

```bash
git switch development && git pull
# bump version in pyproject.toml and add a CHANGELOG entry
gh pr create --base main --head development
# once checks pass and the PR merges:
git switch main && git pull
git tag v0.1.0 && git push origin v0.1.0
```

---

## Critical rules

### Follow the Swift code, not the Swift docs

`Docs/PROJECT_MD_REFERENCE_v4.md` in SwiftProyecto is stale in several places
(TTS key names, episode template syntax, intro/outro resolution). The Swift
*source* is the reference. Divergences are tabulated in REQUIREMENTS.md as
D1–D9; each one has a rationale and a test.

### Never let a Python YAML loader type values

Two conversions silently corrupt real files, and both are disabled in
`yamlcompat.py`:

- YAML 1.1 bools (`no` → `False`) would destroy the Norwegian language code.
  ruamel defaults to YAML 1.2, and `test_yaml_compat.py` asserts it rather than
  trusting it.
- Implicit timestamps would make date handling differ from Swift's. The
  timestamp resolver is removed, so date-shaped scalars stay strings and
  `models.parse_timestamp` is the single date rule. Removing that resolver is
  also what lets `created:` be emitted unquoted, the way Swift writes it.

### The loaded YAML mapping is the source of truth

`document.data` holds it; `document.front_matter` is derived from it and
re-derived after every edit. Do not add an API that mutates the typed model and
writes from it — that is how a write starts diverging from what was validated.

### Never `copy.deepcopy` a loaded YAML structure, and never reorder one

Both detach ruamel's comments from their keys, and the re-emitted block
(`cast:   -`) no longer parses — a valid file silently becomes broken. Use
`parser._clone`, which round-trips through text, and keep canonical key
ordering for documents built from the typed model. Corpus tests catch this.

### Keep diffs minimal

`with_updates` preserves comments, key order, and the flow/block style of a
value it replaces. An edit to a hand-maintained file should be a two-line diff,
not a reformat.

### `ClassVar`, never `Final`, on a slots dataclass

A `Final` class attribute on `@dataclass(frozen=True, slots=True)` becomes a
slot descriptor rather than a constant, and the unknown-key computation breaks
at runtime.

### Writes rotate, never overwrite

`writer.write_text` moves the existing file to `<stem>.<n><ext>` before writing,
numbering at `max(existing) + 1`, and never prunes. Content is staged in a temp
file and `os.replace`d into place. Do not add a path that writes over a file
directly; `backup=False` exists but is not the default.

### Unknown keys are data

Anything not modeled goes to `extra`, at the top level and inside seasons,
languages, variants, and `tts`. A read-write cycle must not lose a key. The
corpus tests enforce this against real files.

---

## Layout

| Module | Role |
|---|---|
| `yamlcompat.py` | The one YAML configuration; the platform-difference guards |
| `models.py` | Frozen dataclasses, strict coercion, v3 migration |
| `parser.py` | Front-matter splitting, `ProjectDocument`, edit methods |
| `writer.py` | Backup rotation, atomic writes, restore |
| `validator.py` | Swift-identical messages; extra checks kept separate |
| `resolver.py` | Variant → season → master resolution |
| `discovery.py` | `find_project_md`, file classification, variant loading |
| `episodes.py` | `<season>`-style path templates |
| `settings.py` | App-specific settings sections |

## Tooling

`uv` for everything. `make help` lists targets: `install`, `lint`, `format`,
`typecheck`, `test`, `cov`, `build`.

- mypy runs strict over `src`; tests are checked with annotation rules relaxed.
- `tests/fixtures/corpus/` — 17 files whose **shapes** came from real projects
  and whose **content is invented**. This repo is public and the real files hold
  unreleased work, so never commit one verbatim; copy the shape and replace the
  content. `test_fixture_hygiene.py` enforces this and checks the corpus still
  covers every shape. Each fixture must parse, round-trip byte-identically,
  survive an edit without losing keys, and validate cleanly.
- `tests/fixtures/doc-examples/` — 11 examples extracted verbatim from
  SwiftProyecto's `Docs/`; the only non-synthetic master/variant coverage.
- `tests/fixtures/adversarial/` — 13 files that must *fail*, or parse in a
  specific way: encoding and YAML edge cases.
- `tests/` is a package (`__init__.py`) so mypy's per-module overrides apply.
