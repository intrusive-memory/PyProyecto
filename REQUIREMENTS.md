---
type: requirements
name: PyProyecto Requirements
description: Requirements for pyproyecto, a pip-installable Python reader and writer for SwiftProyecto's PROJECT.md format
updated: 2026-09-19
state: settled
---

# PyProyecto

A Python port of the PROJECT.md parser from [SwiftProyecto](https://github.com/intrusive-memory/SwiftProyecto), published to PyPI so Python tools, scripts, notebooks, and pipelines can read and edit project metadata without shelling out to `proyecto`.

The design was approved on 2026-09-19 and is folded in below: this document describes what 0.1.0 does, not what was once proposed.

This is the first library under `~/Projects/python`, so it also sets the conventions later Python packages will follow.

**Reference implementation:** SwiftProyecto 5.0.0, schema version 5.
Files that define the behavior:
`Sources/SwiftProyecto/Utilities/ProjectMarkdownParser.swift`,
`Models/ProjectFrontMatter.swift`, `Models/{SeasonDefinition,LanguageDefinition,VariantReference,TTSConfig,FilePattern}.swift`,
`Utilities/ProjectValidator.swift`, `Services/{VariantResolver,ProjectDiscovery,EpisodePathResolver}.swift`.

## Requirements

1. Pure-Python package, installable with `pip install pyproyecto`. The import name is `pyproyecto`. Both `pyproyecto` and `proyecto` are unclaimed on PyPI as of 2026-09-17.
2. Python **3.11+**. 3.11 is the first version where `datetime.fromisoformat` accepts a trailing `Z`.
3. Exactly one runtime dependency: `ruamel.yaml>=0.18` (settled decision 1). Models are stdlib `dataclasses`, not pydantic. This matches the zero-dependency approach in [[swiftescribo-is-org-fountain-parser]].
4. Fully typed. Ships `py.typed` and passes `mypy --strict`.
5. Scope is **schema versions 3, 4, and 5**, the same range SwiftProyecto reads.
6. **Writes are non-destructive.** PyProyecto writes PROJECT.md (this overrides the read-only default originally proposed in open question 2). Every write rotates the existing file to `<stem>.<n><ext>` first, so no write can be the last word — see F9. SwiftProyecto's one-writer rule (`Docs/PROJECT_MD_RULES.md`) now has a second implementation to keep in step; defect D1 is the reason the Python writer re-emits every nested key rather than copying Swift's emitter.
7. Cast is out of scope. Since schema v5, `CAST.md` belongs to SwiftReparto. PyProyecto does not model cast. It only detects a legacy `cast:` block and preserves it as opaque data.
8. Library only, with no CLI in 0.1 (settled decision 4).
9. Behavior matches the Swift reference on a **shared fixture corpus** (see Conformance). Where the Swift code and its docs disagree, the choice is recorded in this file and not left to whoever implements it.
10. MIT license, the same as SwiftProyecto.

## Functionality

### F1. Front-matter splitting

1. `parse(text: str) -> ProjectDocument` and `parse_file(path: str | os.PathLike) -> ProjectDocument`. Files are read as UTF-8.
2. Delimiters follow Swift: the first line whose whitespace-trimmed content is `---`, then the next such line. Swift does **not** require the opening `---` to be on line 1 (settled decision 5).
3. The body is every line after the closing delimiter, joined with `\n` and stripped of leading and trailing whitespace.
4. If either delimiter is missing, raise `NoFrontMatterError`.
5. Keep `raw_front_matter: str` (the exact YAML text), `raw_text: str`, and `leading_text: str` (anything before the opening delimiter) on the document. `raw_text` is what makes an unmodified write byte-identical (F10.4); `leading_text` is what lets such a document be written back without losing the content that preceded its front matter.

### F2. YAML loading. This is the biggest risk in the port.

Swift decodes YAML → JSON → `Codable`. Python YAML loaders add implicit typing that Swift never does. The loader **must**:

1. Treat `yes/no/on/off/y/n` as **strings**. This is the YAML 1.1 "Norway problem": `languages: [es, no]` must not become `['es', False]`.
2. **Not** auto-convert timestamps. `created: 2025-01-25T00:00:00Z` is parsed into a datetime by F3, not by the YAML layer, so both paths have one validation rule.
3. Keep integers as `int` and floats as `float`. Unquoted `model: 1.7b` stays a string. Unquoted `model: 0.6` would be a float. Swift would reject that as a type mismatch, and so must PyProyecto.
4. Keep mapping key order, so unknown keys come back in document order.
5. Raise `InvalidYAMLError(message, line, column)` when available. Swift exposes no position, and Python should do better.

### F3. Data model (frozen dataclasses)

All model types are `@dataclass(frozen=True, slots=True)`. `ProjectFrontMatter` has field names in snake_case and a documented mapping to camelCase YAML keys:

| YAML key | Python field | Type | Required |
|---|---|---|---|
| `type` | `type` | `str` | yes |
| `title` | `title` | `str` | yes |
| `author` | `author` | `str` | yes |
| `created` | `created` | `datetime` (tz-aware, UTC) | yes |
| `updated` | `updated` | `datetime \| None` | |
| `description`, `genre` | same | `str \| None` | |
| `tags` | `tags` | `tuple[str, ...] \| None` | |
| `episodesDir`, `audioDir`, `exportFormat` | `episodes_dir`, `audio_dir`, `export_format` | `str \| None` | |
| `filePattern` | `file_pattern` | `FilePattern \| None` | |
| `introFile`, `outroFile` | `intro_file`, `outro_file` | `str \| None` | |
| `preGenerateHook`, `postGenerateHook` | `pre_generate_hook`, `post_generate_hook` | `str \| None` | |
| `tts` | `tts` | `TTSConfig \| None` | |
| `schemaVersion` | `schema_version` | `int \| None` (as declared) | |
| `projectType` | `project_type` | `str \| None` | |
| `seasons` | `seasons` | `tuple[SeasonDefinition, ...] \| None` | |
| `languages` | `languages` | `tuple[LanguageDefinition, ...] \| None` | |
| `variants` | `variants` | `tuple[VariantReference, ...] \| None` | |
| `episodePath` | `episode_path` | `str \| None` | |
| *(any other key)* | `extra` | `Mapping[str, Any]` (read-only, in order) | |

Nested types copy the Swift structs exactly:

- `SeasonDefinition`: `number: int` (required), `title`, `description`, `episodes: int` (required), `release_date: datetime`, `episodes_dir`, `file_pattern`, `intro_file`, `outro_file`, `tts`.
- `LanguageDefinition`: `code` (required), `name` (required), `locale`.
- `VariantReference`: `season: int`, `language`, `path` (all required), `status: VariantStatus | None` (a `StrEnum` of `published`, `in_progress`, `draft`, `obsolete`; an unrecognized value is an error), `intro_file`, `outro_file`.
- `TTSConfig`: `provider_id`, `voice_id`, `language_code`, `voice_uri` (YAML `voiceURI`), `model`, `action_line_voice`. These are the **code's** keys. The v4 reference doc's `provider`/`voiceLanguage` are stale and are not supported.
- `FilePattern`: keeps whether the source was a single string or a list (`is_single`) and exposes `patterns: tuple[str, ...]`.

Rules:

1. **Dates.** Accept ISO 8601 with a `Z` or offset, and normalize to aware UTC. A string of the wrong form raises `InvalidDateError(field, value)`. Date-only values (`2025-01-15`) are rejected (settled decision 6).
2. **Types are strict, as in Swift `Codable`.** A string where an int is expected (`episodes: "12"`) raises `InvalidYAMLError`. It is not coerced.
3. **A missing required field** raises `MissingRequiredFieldError(field)` and names the dotted path (`seasons[1].episodes`). Swift reports only the leaf key.
4. **v3 migration**, matching Swift: when `seasons` is absent and `season` is present, synthesize `seasons = (SeasonDefinition(number=season, episodes=episodes or 0),)`. `season` and `episodes` are known keys and never land in `extra`.
5. Convenience accessors: `season` and `episodes` (from `seasons[0]`), `detected_schema_version` (declared value or `3`), `is_legacy_v3_format`, and the `resolved_*` defaults (`episodes_dir → "episodes"`, `audio_dir → "audio"`, `file_patterns → ("*.fountain",)`, `export_format → "m4a"`).
6. **Legacy cast.** `has_legacy_cast_key` and `legacy_cast_character_names` read `extra["cast"]`, and nothing more.
7. **Unknown keys nested inside known objects** (for example a season-level `cast:`, or unknown `tts` keys). Swift throws these away silently. PyProyecto keeps them in an `extra` mapping on each nested dataclass, so tools can see them.
8. Each model type carries its own YAML key list as a `ClassVar`, never a bare `Final` annotation: under `slots=True` a `Final` class attribute becomes a slot descriptor rather than a constant, and the "unknown key" computation silently breaks.

### F4. App-specific settings

Python equivalent of `AppFrontMatterSettings`:

These are module-level functions rather than methods, so `ProjectFrontMatter` stays a plain data record:

1. `settings(front_matter, key) -> Mapping | None` returns the raw section. A section that is not a mapping raises `InvalidYAMLError`.
2. `settings_as(front_matter, cls) -> T | None`, where `cls` is a dataclass with `section_key: ClassVar[str]`. Fields are matched in both snake_case and camelCase. Unknown keys in the section are ignored; a missing field with no default raises. Passing a non-dataclass raises `TypeError`.
3. `has_settings(front_matter, key) -> bool`.
4. `with_settings(front_matter, key, section) -> ProjectFrontMatter` returns a copy with that section set.
5. Settings live in `extra`, so a section nobody asks for still survives a read-write cycle.

### F5. Validation

`validate(document | front_matter) -> ValidationResult` accepts either a whole document or bare front matter. `errors` and `warnings` use the same rules and **identical message strings** as `ProjectValidator`, so output from the Swift and Python tools can be diffed directly:

- Empty `title` or `author` is an error. A `type` other than `project` or `overview` (case-insensitive) is an error.
- In v4 and later: duplicate season numbers, `episodes <= 0`, and `number <= 0` are errors. Duplicate or empty language codes are errors. An overview without `variants` is a warning, and an overview with `episodesDir` is a warning.
- In v3: a season or episode count that is not positive is a warning.
- A legacy `cast:` key produces the v5 migration warning, verbatim.
- Metadata includes `schema_version`, `file_type` (`master`/`variant`/`project`), and the season, language, and variant counts and lists.

Checks that go beyond the Swift reference must never contaminate the comparable lists. They go in two separate fields:

- `extra_warnings: tuple[str, ...]` — content before the opening `---` (settled decision 5), a `schemaVersion` newer than 5, and a rendering of each conformance warning.
- `conformance_warnings: tuple[ConformanceWarning, ...]` — the structured form, carrying the field, the message, and the Swift defect id, forwarded from `document.warnings`.

### F6. Variant resolution and discovery

1. `resolve_variant(variant, master, season) -> ProjectFrontMatter` follows `VariantResolver.resolve` field by field. `title`, `author`, and `created` always come from the master. The chain is variant → season → master for `description`, `episodes_dir`, `file_pattern`, `tts`, `intro_file`, and `outro_file`. It is variant → master for everything else. Empty `tags` and empty `extra` count as unset.
2. `find_project_md(start: path) -> Path | None`. If the start is a file, use its directory. If that directory is named `episodes` (case-insensitive), check its parent first, then the directory itself, then its parent.
3. `is_master_file`, `is_variant_file`, and `is_single_project_file` use Swift's predicates.
4. `load_variant(reference, master_path)` resolves `reference.path` against the master's directory. A missing file raises `VariantFileNotFoundError`.
5. `find_variants(master_path) -> list[ProjectFrontMatter]` loads and resolves every variant a master references.

### F7. Episode path templates

`resolve_episode_path(template, *, language, season, episode, ext) -> str` substitutes `<language>`, `<season>`, `<episode>`, and `<ext>` with no zero-padding. This follows the Swift **code**. The `{season}`/`{number:03d}` syntax in `PROJECT_MD_REFERENCE_v4.md` is not implemented (settled decision 7). `extract_template_variables` and `validate_template` are included. Unlike Swift, which always returns `isValid: true`, `validate_template` returns `is_valid=False` when it finds unknown variables.

### F8. Errors

All errors subclass `ProyectoError`: `NoFrontMatterError`, `InvalidYAMLError`, `MissingRequiredFieldError`, `InvalidDateError`, `VariantFileNotFoundError`. Each carries the source path when one is known, and `InvalidYAMLError` carries `line` and `column` when the loader reports them.

`ConformanceWarning` is a frozen dataclass, not an exception: a document that PyProyecto accepts and Swift does not is not an error condition. It carries `field`, `message`, and `swift_defect`.

### F9. Writing

1. `write_text(path, text)` and `write_document(document, path=None)`. Both return the backup path they made, or `None` when there was no existing file.
2. **Rotation.** An existing file is moved to `<stem>.<n><ext>` — `PROJECT.md` → `PROJECT.1.md` → `PROJECT.2.md`. `n` is always `max(existing) + 1`, so deleting a backup never makes a later write reuse its number. Backups are never pruned; `list_backups` exposes them for tools that want to.
3. **Atomicity.** Content is staged in a temporary file in the same directory, `fsync`ed, and then `os.replace`d into place. A reader never sees a partial file, and a failed write leaves the original where it was.
4. `restore_backup(path, backup=None)` puts a backup back, rotating the current file in its turn, so an undo is itself reversible.
5. `backup=False` exists for callers that manage their own history. It is never the default.
6. A full re-emit writes **every** field, including the nested season and variant keys Swift's writer drops (D1). This is what makes a Python read-write cycle lossless where the Swift one is not.
7. Every write stamps `schemaVersion: 5`.

### F10. Document model and edit semantics

`ProjectDocument` is what `parse` returns. Its design is the reason a write cannot quietly diverge from what was validated.

1. **The loaded YAML mapping is the source of truth.** `document.data` holds it, including every unknown key. `document.front_matter` is *derived* from it, and every edit re-derives it. A typed view that could drift from the bytes on disk is the failure mode this avoids.
2. **Two edit paths**, because they trade off differently:
   - `with_updates({...})` edits the loaded mapping. Comments, key order, and quoting survive, and existing keys keep their position while new keys are appended. This is the path for files people maintain by hand. A value of `None` removes a key.
   - `with_front_matter(fm)` re-emits from the typed model in canonical key order (Swift's emitter order). Cleaner output; comments are lost.
   `with_body(text)` replaces the body alone; `ProjectDocument.new(fm, body)` builds one from scratch.
3. **Never reorder an existing document's keys, and never `copy.deepcopy` a loaded structure.** Both detach ruamel's comments from the keys they belong to, and the re-emitted block (`cast:   -`) no longer parses — a valid file silently becomes a broken one. Cloning round-trips through YAML text instead. Canonical ordering applies only to documents built from the typed model, where there are no comments to lose.
4. **An unmodified document renders as the bytes it was parsed from.** `document.is_modified` reports which case applies. Reading and writing without edits changes nothing.
5. **A replaced value keeps the style of the value it replaced.** Handing `with_updates` a plain list for a flow-style `tags: [a, b]` re-emits flow style, so an edit to a hand-maintained file produces a minimal diff rather than a reformat.

## Out of scope

LLM project generation (`proyecto init` / `generate-project`), `proyecto migrate` and anything that calls `reparto`, CAST.md, the ProjectBrowser UI, SwiftData models, bookmarks, git file sources, directory structure recognition, and `ParseBatchConfig` audio iteration.

## Conformance

Rather than freezing an expected JSON blob per fixture — which would have to be regenerated on every field addition and would encode today's bugs as tomorrow's baseline — each corpus file is asserted against four invariants, parametrized per file:

1. It parses, with a non-empty title and author.
2. It **round-trips byte-identically** when unmodified.
3. It **survives an edit without losing keys**: every key present before is present after, the body is unchanged, and any legacy cast names are intact.
4. It validates without errors.

Named cases then assert the specific behaviors that matter (the shorthand `languages:` list, `episodes:` without `season:`, the master/variant file, nested unknown keys).

The fixture tree:

- `tests/fixtures/corpus/` — 17 files whose **shapes** were taken from real projects and whose **content is invented**. This repository is public and the source files are unreleased work, so no real file is committed; `test_fixture_hygiene.py` enforces that and asserts the corpus still covers every shape. Between them they cover legacy `cast:`, `episodes_index`, `episodeList`, v3 `season`/`episodes`, a shorthand `languages:` list, `episodes:` without `season:`, and comment-bearing cast blocks.
- `tests/fixtures/doc-examples/` — 11 worked examples extracted verbatim from `Docs/EXAMPLE_PROJECT_v4.md` and `PROJECT_MD_REFERENCE_v4.md`. They are the only non-synthetic coverage of the master/variant and multi-season shapes, since no real project uses them yet. Illustrative skeletons containing `...` placeholders are not valid YAML and are excluded.
- `tests/fixtures/adversarial/` — 13 files that must fail, or must parse in a specific way: the Norway problem, unquoted numeric `model`, a stringy episode count, CRLF, a BOM, `---` inside the body, content before the front matter, a date without a timezone, a date-only value, `schemaVersion: 99`, nested unknown keys, a file with no front matter, and the reserved-indicator `author:` from D10.

A real file that exposes a new shape gets added to the corpus rather than reduced to a unit test.

Still outstanding: a CI job that runs the Swift parser over the same corpus and diffs normalized JSON against Python. It is blocked on a `proyecto dump --json` subcommand that SwiftProyecto does not have (settled decision 8). Until then, "matches Swift" means "matches a careful reading of the Swift source".

## Swift reference defects found while writing this

The port must not reproduce these. Each needs a SwiftProyecto issue.

| # | Defect | Where | PyProyecto stance |
|---|---|---|---|
| D1 | `generate()` drops `seasons[].filePattern`, `introFile`, `outroFile`, `tts` and `variants[].introFile`, `outroFile` on write, so a read-then-write loses data | `ProjectMarkdownParser.generate` | Not reproduced: a full re-emit writes every nested key, and a regression test asserts it (F9.6). The Swift bug still needs fixing, or a Swift write will undo what a Python write preserved. |
| D2 | `episodes: N` with no `season:` is decoded and then thrown away (`confessions/PROJECT.md` has this) | `ProjectFrontMatter.init(from:)` | Settled decision 3: accept and warn |
| D3 | `languages: [es, fr, …]` (string list, used by `lingua-matra`) does not decode into `[LanguageDefinition]`, so Swift appears to reject the file | `LanguageDefinition` | Settled decision 3: accept and warn |
| D4 | Unknown keys inside `seasons[]` and `tts` are silently discarded | nested `Codable` structs | Preserve in `extra` (F3.7) |
| D5 | Docs say `tts.provider`/`voiceLanguage`, but the code uses `providerId`/`voiceId`/`languageCode`/… | `PROJECT_MD_REFERENCE_v4.md` | Follow the code |
| D6 | Docs give `{season}`/`{number:03d}` template syntax, but the code uses `<season>`/`<episode>` without padding | `EpisodePathResolver` vs docs | Follow the code (settled decision 7) |
| D7 | `introFile` is documented as relative to the project root, but `resolvedIntroOutroAssets` checks for it under `episodesDir` | `ProjectFrontMatter` | Resolve against the project root. Asset existence checks are not ported. |
| D8 | `ProjectFrontMatter.isValid` returns false for `type: overview` | `ProjectFrontMatter` | Not ported. Use `validate()`. |
| D9 | `validateTemplate` always returns `isValid: true` | `EpisodePathResolver` | Fixed in Python (F7) |
| D10 | One real project file has an `author:` value beginning with `@`. `@` is a reserved indicator in YAML, so that is not a valid plain scalar | that file, not the library | Rejected with a line/column. The file needs fixing (quote the value); worth checking whether Swift's YAML parser accepts it, because if it does, the two implementations disagree on a real file |

### Python-side hazards found during implementation

- **`copy.deepcopy` on a ruamel structure corrupts it.** Deep-copying a loaded document detaches comments from their keys, and the re-emitted result (`cast:   -`) no longer parses — it silently turns a valid file into a broken one. Cloning goes through YAML text instead (`parser._clone`). A corpus test covers it.
- **ruamel quotes timestamp-shaped strings on output.** Removing the implicit `timestamp` resolver is what lets `created:` round-trip unquoted, matching Swift's output byte for byte.
- **`Final` on a `slots=True` dataclass becomes a slot, not a constant.** The per-type YAML key lists must be `ClassVar`; annotated `Final`, they turn into member descriptors and every "unknown key" computation raises at runtime (F3.8).
- **A flow-style value replaced with a plain Python list re-emits as a block list.** Left alone, a one-line `tags: [a, b]` becomes six lines and the diff buries the actual change (F10.5).

## Repository conventions (new `~/Projects/python` pattern)

Settled on 2026-09-19 and implemented here. Later Python packages copy this scaffolding rather than re-deciding it.

- `uv` for environments, locking, and builds, with the `uv_build` backend and a `src/` layout. `.python-version` pins the floor (3.11), not the newest interpreter.
- A `Makefile` with a `help` target, matching the Swift repos: `make install | lint | format | typecheck | test | cov | build | clean | help`.
- `ruff` (lint and format), `mypy`, `pytest` with coverage.
- **mypy is strict over `src`.** `tests/` is a package (it has an `__init__.py`) so that per-module overrides apply to it; there, annotation rules are relaxed and `union-attr`/`index` are disabled, because asserting on an `Optional` is the point of a test.
- Licensing uses `license = "MIT"` in `pyproject.toml`. The `License ::` trove classifier is deprecated under PEP 639 and is omitted.
- GitHub repo `intrusive-memory/PyProyecto`. The `development` → `main` branch flow and release-by-tag match the Swift libraries.
- CI on `ubuntu-latest` (pure Python, so no macOS runner is needed) with a 3.11–3.14 matrix, in two jobs: `test` and `quality` (ruff check, ruff format --check, mypy). Publishing uses **PyPI Trusted Publishing** (OIDC, no API token), triggered by a GitHub release.
- The package version is independent of SwiftProyecto. The README states which **schema** versions are supported, not which Swift version.
- `AGENTS.md`, `CLAUDE.md`, and `CHANGELOG.md` follow the Swift repos' format. Every Markdown file carries `type:` in YAML frontmatter, per the global policy — including `README.md`, which means the rendered PyPI description opens with a frontmatter block.

## Settled decisions

Every question below was resolved on 2026-09-19. Where the answer differs from the default proposed on 2026-09-17, the reason is given.

| # | Question | Decision |
|---|---|---|
| 1 | Which YAML library? | **`ruamel.yaml`**, the proposed default. YAML 1.2 (no Norway problem), preserves key order and comments, reports error positions. Its round-trip mode is what makes comment-preserving writes possible. |
| 2 | Will PyProyecto ever write PROJECT.md? | **Yes, in 0.1** — the user overrode the read-only default and asked for a writer whose export moves the old version aside. See F9. Both edit paths keep the loaded YAML as the source of truth, which is what stops D1-style key loss. |
| 3 | Real files Swift mishandles (D2, D3) | **Be lenient and warn**, as proposed. Both cases are reported as `ConformanceWarning`s tagged with the Swift defect, available on `document.warnings` and surfaced through `ValidationResult.conformance_warnings` (structured) and `extra_warnings` (rendered). Swift should be fixed to match. |
| 4 | Ship a CLI? | Not in 0.1; revisit at 0.2 with `pyproyecto validate` and `dump --json`. `dump --json` is also the harness for the differential test in question 8. |
| 5 | Require `---` on line 1? | Parse like Swift (delimiter anywhere), and warn. The warning is in `extra_warnings`, not the Swift-comparable `warnings` list. |
| 6 | Date-only and naive datetimes? | Rejected, with an `InvalidDateError` naming the expected format. |
| 7 | Episode template syntax | The code's `<season>` syntax. The Swift docs need fixing. |
| 8 | Swift-vs-Python differential test in CI | Wanted, still blocked: it needs a `proyecto dump --json` subcommand that SwiftProyecto does not have. Until then, "matches Swift" means "matches a careful reading of the Swift source". |
| 9 | Add to `package-collection/collection.json`? | No — that is a Swift Package Collection. |
| 10 | Monorepo or one repo per package? | One git repo per package; `~/Projects/python` is just a parent directory. |

## Status

0.1.0 is implemented and published to <https://github.com/intrusive-memory/PyProyecto>
(public). F1-F10 are done, with 212 tests, and `ruff` and `mypy --strict` clean.
The fixture tree holds 17 corpus files, 11 doc examples, and 13 adversarial
files.

**Pipeline** (see [RELEASING.md](RELEASING.md)): `development` -> `main` ->
tagged release -> PyPI. `main` is protected, requires the four `Unit tests`
checks plus `Lint and type check`, enforces linear history, and rejects direct
pushes including from admins. That rejection is verified, not assumed.

**The fixture corpus is synthetic.** Shapes came from real projects; content is
invented, because this repository is public and the source files hold
unreleased work. `test_fixture_hygiene.py` blocks a verbatim copy and asserts
the corpus still covers every shape.

Follow-up work:

1. **PyPI is the final action and is not done yet.** The `pypi` job is skipped
   until the repository variable `PYPI_PUBLISH` is `true`, which needs a PyPI
   account and a Trusted Publisher that only a human can create. RELEASING.md
   step 4 has the exact form values. Until then `pip install pyproyecto` does
   not work.
2. File D1-D10 as SwiftProyecto issues. D1 is the urgent one: until it is
   fixed, a Swift write drops the nested season keys a Python write preserves.
3. Fix the one real project file whose `author:` value starts with `@`.
4. Add `proyecto dump --json` to SwiftProyecto, then wire up the differential
   CI job (settled decision 8).
5. Revisit the CLI at 0.2 (settled decision 4).
