---
type: reference
name: PyProyecto README
description: Read and write SwiftProyecto's PROJECT.md format from Python
updated: 2026-09-19
---

# PyProyecto

Read and write [SwiftProyecto](https://github.com/intrusive-memory/SwiftProyecto)'s
`PROJECT.md` format from Python.

`PROJECT.md` is a Markdown file with YAML front matter that describes a content
project — title, author, seasons, episode layout, TTS configuration. SwiftProyecto
owns the format; PyProyecto is a faithful Python reader for it, so scripts,
notebooks, and pipelines can use project metadata without shelling out to the
`proyecto` binary.

Supports schema versions **3, 4, and 5**. Requires Python 3.11+.

```bash
pip install pyproyecto
```

## Reading

```python
from pyproyecto import parse_file, validate

doc = parse_file("PROJECT.md")
fm = doc.front_matter

print(fm.title, fm.author, fm.created)
print(fm.resolved_episodes_dir, fm.resolved_file_patterns)

result = validate(doc)
if not result.is_valid:
    for error in result.errors:
        print("error:", error)
```

Unknown keys are never dropped. Anything PyProyecto does not model is kept in
`front_matter.extra` (top level) or the `extra` of the object it appeared in
(a season, a `tts` block), and written back unchanged.

## Writing, and why it cannot destroy your file

Every write rotates the file already on disk before the new one lands:

```python
from pyproyecto import parse_file, write_document

doc = parse_file("PROJECT.md").with_updates({"genre": "Documentary"})
backup = write_document(doc)   # PROJECT.md -> PROJECT.1.md, then writes PROJECT.md
print(backup)                  # PROJECT.1.md
```

The next write makes `PROJECT.2.md`, and so on. Numbering is always
`max(existing) + 1`, so deleting an old backup never causes a later write to
reuse its number, and nothing is ever pruned automatically. Content is staged in
a temporary file and moved into place, so a reader never sees a half-written
file, and a failed write leaves the original untouched.

To undo:

```python
from pyproyecto import list_backups, restore_backup

list_backups("PROJECT.md")     # [PROJECT.1.md, PROJECT.2.md]
restore_backup("PROJECT.md")   # restores the newest, rotating the current file first
```

`with_updates` preserves comments, key order, and quoting — use it on files
people maintain by hand. `with_front_matter` re-emits the whole document in
canonical key order, which is cleaner but drops comments. An unmodified
document writes back byte-for-byte identical.

## Organizing a multi-file project

This is what the format is for: a folder of screenplays (or any composition
files) with one `PROJECT.md` declaring how it is laid out, so tools stop
guessing. **[ADOPTING.md](ADOPTING.md) is the full guide** — including a
procedure for agents.

Turn an existing folder into a project:

```python
from pyproyecto import audit_layout, parse_file, scaffold_project, write_document

doc = scaffold_project("~/screenplays/the-long-tide", author="Your Name")
print(doc.to_text())                 # review before writing
write_document(doc, "~/screenplays/the-long-tide/PROJECT.md")

audit = audit_layout(parse_file("~/screenplays/the-long-tide/PROJECT.md"))
print(audit.is_clean, audit.warnings)
```

`scan_directory` detects flat folders, an `episodes/` subdirectory, and season
directories (`season-1`, `s02`), and `filePattern` covers the extensions
actually present — so you declare the layout you already have rather than
reorganizing to fit the tool.

Then work with it:

```python
from pyproyecto import episode_files, find_project_md, parse_file

find_project_md("episodes/chapter-3.fountain")     # -> Path("PROJECT.md")

doc = parse_file("PROJECT.md")
episode_files(doc)                                  # natural order: 1, 2, 10
episode_files(doc, season=2)                        # season overrides applied
audit_layout(doc).unmatched_files                   # files no pattern covers
```

`resolve_layout` returns the whole picture — episodes directory, audio
directory, patterns, resolved intro/outro assets, and the files that exist.
`audit_layout` is the check to run after adding files: it reports a declared
episode count that has drifted, a named file that is missing, and composition
files no `filePattern` matches.

## Creating a file from scratch

```python
from datetime import UTC, datetime
from pyproyecto import ProjectDocument, ProjectFrontMatter, write_document

fm = ProjectFrontMatter(
    type="project",
    title="My Podcast",
    author="Tom Stovall",
    created=datetime.now(UTC),
    episodes_dir="episodes",
    audio_dir="audio",
)
write_document(ProjectDocument.new(fm, body="# My Podcast"), "PROJECT.md")
```

Every write stamps `schemaVersion: 5`.

## YAML differences from the Swift implementation

Swift parses YAML into JSON and decodes that, so scalars arrive as strings,
numbers, or bools. Python YAML loaders type more aggressively, and two of those
conversions would corrupt real project files. PyProyecto disables both:

| Hazard | What a default Python loader does | PyProyecto |
|---|---|---|
| `languages: [es, no]` | YAML 1.1 reads `no` as `False`, losing the Norwegian language code | Stays the string `"no"` |
| `created: 2025-01-25T00:00:00Z` | Becomes a `datetime` during loading, so date rules differ between the two implementations | Stays a string; one rule validates it |

Numbers keep YAML semantics: `model: 1.7b` is a string, while `model: 0.6` is a
float and is rejected, exactly as Swift's decoder would reject it. Dates must be
ISO 8601 with a timezone; `2025-01-15` and naive datetimes are errors.

## Where PyProyecto knowingly differs from SwiftProyecto

The port follows the Swift *code*, not its documentation, wherever the two
disagree. It is also more permissive in two places where the Swift
implementation loses real data, and it reports each of those through
`result.extra_warnings`:

- `languages: [es, fr]` (a shorthand real projects use) is read as language
  definitions rather than rejected.
- `episodes: 72` with no `season:` keeps its episode count instead of
  discarding it.

Unknown keys nested inside seasons and `tts` blocks are preserved rather than
dropped, and a re-emit keeps season-level `filePattern`, `introFile`,
`outroFile`, and `tts`. See `REQUIREMENTS.md` for the full list with references
to the Swift source.

Cast is not modeled. Since schema v5 a production's cast lives in `CAST.md`,
owned by [SwiftReparto](https://github.com/intrusive-memory/SwiftReparto). A
legacy `cast:` block is preserved verbatim and reported by
`front_matter.has_legacy_cast_key`.

## Development

```bash
make help       # list targets
make install    # uv sync --all-groups
make test       # pytest
make lint       # ruff check + format --check
make typecheck  # mypy --strict
```

The test corpus in `tests/fixtures/corpus/` holds real `PROJECT.md` files, and
`tests/fixtures/doc-examples/` holds examples taken from SwiftProyecto's docs.
Every one must parse, round-trip byte-identically when unmodified, survive an
edit without losing keys, and validate cleanly. `tests/fixtures/adversarial/`
holds the files that must fail, and the encoding and YAML edge cases.

## License

MIT
