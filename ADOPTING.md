---
type: reference
name: Adopting the PROJECT.md pattern
description: How to turn a folder of screenplays, or any set of composition files, into a declared project
updated: 2026-09-19
---

# Adopting the PROJECT.md pattern

You have a folder of screenplays. Tools and agents that work on it have to
guess: which files are episodes, what order they go in, where the audio should
land, who wrote it. Every tool guesses differently, and every guess breaks when
someone adds a file.

`PROJECT.md` replaces the guessing with a declaration. One Markdown file at the
root of the folder, with YAML front matter that says what the project is and
how it is laid out. Tools read it instead of inferring.

This guide is for turning an existing folder into one. It takes about a minute.

---

## The shortest version

```bash
pip install git+https://github.com/intrusive-memory/PyProyecto
```

```python
from pyproyecto import scaffold_project, write_document, audit_layout, parse_file

# 1. Look at the folder and propose a PROJECT.md for it.
doc = scaffold_project("~/screenplays/the-long-tide", author="Your Name")

# 2. Review it, then write it. An existing PROJECT.md is rotated to
#    PROJECT.1.md rather than overwritten.
print(doc.to_text())
write_document(doc, "~/screenplays/the-long-tide/PROJECT.md")

# 3. Check that the declaration matches what is actually on disk.
audit = audit_layout(parse_file("~/screenplays/the-long-tide/PROJECT.md"))
print(audit.errors, audit.warnings)
```

What comes out looks like this:

```markdown
---
type: project
title: The Long Tide
author: Your Name
created: 2026-09-19T00:00:00Z
schemaVersion: 5
seasons:
  - number: 1
    episodes: 12
episodesDir: episodes
audioDir: audio
filePattern: '*.fountain'
exportFormat: m4a
---
```

Everything below the front matter is yours: notes, a synopsis, production
history. Tools only read the front matter.

---

## What the fields mean

| Field | What it declares |
|---|---|
| `type` | `project` for a single project, `overview` for an index of variants |
| `title`, `author`, `created` | Required. `created` must be ISO 8601 with a timezone |
| `episodesDir` | Where the composition files live, relative to PROJECT.md |
| `filePattern` | Which files count: a glob, a list of globs, or an explicit file list |
| `audioDir` | Where generated audio goes |
| `seasons` | Per-season episode counts and directory overrides |
| `introFile`, `outroFile` | Assets wrapped around each episode, relative to the project root |
| `tts` | Voice provider configuration |

Any key the library does not recognize is **preserved, not discarded** — your
own tooling can add keys and they survive a read-write cycle.

A production's cast does **not** live here. It belongs in `CAST.md`, owned by
[SwiftReparto](https://github.com/intrusive-memory/SwiftReparto).

---

## The layouts it understands

`scaffold_project` detects all of these. You do not have to reorganize
anything to adopt the pattern — declare the layout you already have.

### Flat: everything in one folder

```
the-long-tide/
├── PROJECT.md
├── chapter-1.fountain
├── chapter-2.fountain
└── chapter-10.fountain
```

```yaml
episodesDir: .
filePattern: "*.fountain"
```

### An episodes subdirectory

```
the-long-tide/
├── PROJECT.md
├── audio/
└── episodes/
    ├── chapter-1.fountain
    └── chapter-2.fountain
```

```yaml
episodesDir: episodes
filePattern: "*.fountain"
```

### Seasons

Subdirectories named `season-1`, `season_2`, `s03`, or `Season 4` are
recognized and become a `seasons` array:

```
the-long-tide/
├── PROJECT.md
└── episodes/
    ├── season-1/
    │   ├── a.fountain
    │   └── b.fountain
    └── season-2/
        └── c.fountain
```

```yaml
seasons:
  - number: 1
    episodes: 2
    episodesDir: episodes/season-1
  - number: 2
    episodes: 1
    episodesDir: episodes/season-2
```

A season can override `episodesDir`, `filePattern`, `introFile`, `outroFile`,
and `tts`. Anything it does not override comes from the project level.

### Mixed file types

If the folder holds `.fountain` and `.highland` files, `filePattern` covers
both, most common first:

```yaml
filePattern: ["*.fountain", "*.highland"]
```

Recognized composition extensions: `.fountain`, `.highland`, `.fdx`, `.guion`,
`.md`, `.markdown`, `.txt`, `.rtf`, `.pdf`, `.docx`, `.odt`.

### Multi-language: a master and its variants

For the same production in several languages, one master file indexes the
variants:

```yaml
type: overview
title: The Long Tide
author: Your Name
created: 2026-09-19T00:00:00Z
languages:
  - code: en
    name: English
  - code: es
    name: Español
variants:
  - season: 1
    language: en
    path: episodes/season-1/PROJECT_en.md
    status: published
  - season: 1
    language: es
    path: episodes/season-1/PROJECT_es.md
    status: in_progress
```

Each variant is a normal `type: project` file and may be sparse; anything it
omits is inherited:

```python
from pyproyecto import find_variants

for variant in find_variants("PROJECT.md"):
    print(variant.title, variant.episodes_dir)  # resolved against the master
```

Resolution order is **variant → season → master**, except `title`, `author`,
and `created`, which always come from the master.

---

## Working with a project once it exists

### Find the PROJECT.md from any file in the project

```python
from pyproyecto import find_project_md

find_project_md("episodes/chapter-3.fountain")   # -> Path("PROJECT.md")
```

It checks the file's directory, and if that directory is named `episodes`, its
parent first.

### List the episode files, in order

```python
from pyproyecto import episode_files, parse_file

for path in episode_files(parse_file("PROJECT.md")):
    print(path)          # chapter-1, chapter-2, chapter-10 -- natural order
```

Season-specific:

```python
episode_files(doc, season=2)
```

### Check the declaration still matches the folder

```python
from pyproyecto import audit_layout

audit = audit_layout(parse_file("PROJECT.md"))
if not audit.is_clean:
    print(audit.errors)            # episodesDir missing, named file absent
    print(audit.warnings)          # count drift, unmatched files, missing intro
    print(audit.unmatched_files)   # composition files no filePattern covers
```

This is the check to run after adding files. A new screenplay that no
`filePattern` matches shows up here rather than being silently ignored.

### Edit it without destroying it

```python
from pyproyecto import parse_file, write_document

doc = parse_file("PROJECT.md").with_updates({"genre": "Drama"})
backup = write_document(doc)     # PROJECT.md -> PROJECT.1.md, then writes
```

Comments, key order, and quoting are preserved, so the diff is the line you
changed. Every write rotates the previous version to `PROJECT.<n>.md` and
nothing is ever pruned, so a bad edit is one rename away from undone.

---

## For agents

If you are an agent asked to "turn this folder into a project", or to adopt the
PROJECT.md pattern for a repository, this is the procedure:

1. **Scan before proposing.** `scan_directory(path)` reports the layout,
   extensions, season directories, and whether a `PROJECT.md` already exists.
   Do not assume a layout.
2. **If `scan.existing_project` is set, do not scaffold over it.** Parse it,
   run `audit_layout`, and report the drift. Scaffolding replaces a file
   someone wrote by hand; rotation makes that recoverable but still surprising.
3. **Ask for `author` — do not invent one.** It is required, and guessing it
   wrongly puts a name in a file that gets committed.
4. **Show the proposed front matter before writing it.** `doc.to_text()`
   renders it. The person adopting should see what they are getting.
5. **Write with `write_document`**, never by rendering to a string and calling
   `Path.write_text`. The rotation and the atomic replace are the point.
6. **Audit after writing** and report the result. A clean audit is the evidence
   that the declaration is true; anything else needs a human decision.
7. **Never invent content.** `description`, `genre`, and `tags` are optional.
   Leave them out rather than guessing at what a screenplay is about.

A complete, honest adoption run:

```python
from pyproyecto import (
    audit_layout, parse_file, scaffold_project, scan_directory, write_document,
)

scan = scan_directory(folder)
if scan.existing_project:
    audit = audit_layout(parse_file(scan.existing_project))
    report(audit)                      # do not overwrite; report and stop
else:
    doc = scaffold_project(folder, author=author_supplied_by_the_user)
    show(doc.to_text())                # let them see it first
    write_document(doc, scan.root / "PROJECT.md")
    report(audit_layout(parse_file(scan.root / "PROJECT.md")))
```

---

## Questions people ask

**Do I have to move my files?** No. Declare the layout you have. The scaffolder
detects flat folders, `episodes/` subdirectories, and season directories.

**What if the folder already has a PROJECT.md?** Parse it and audit it instead
of scaffolding. If you do rescaffold, the old file is rotated to `PROJECT.1.md`.

**What happens when I add an episode?** Nothing breaks — a glob picks it up.
Run `audit_layout` to catch a count that has drifted, or a file whose extension
no pattern covers.

**Can I put my own fields in it?** Yes. Unknown keys are preserved through
read-write cycles. Namespace them under a key of your own rather than adding
top-level keys that might collide with a future schema version.

**Is this the same format Swift tools use?** Yes.
[SwiftProyecto](https://github.com/intrusive-memory/SwiftProyecto) owns the
format and the `proyecto` CLI; PyProyecto is the Python reader and writer for
the same files, schema versions 3 through 5.
