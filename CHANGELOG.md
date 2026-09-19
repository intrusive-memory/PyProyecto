---
type: reference
name: CHANGELOG
description: Release history for PyProyecto
updated: 2026-09-19
---

# Changelog

All notable changes to PyProyecto are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — unreleased

First release. Ports SwiftProyecto 5.0.0's PROJECT.md handling (schema v3/v4/v5).

### Added

- `parse` / `parse_file` with strict, Swift-compatible decoding, and errors that
  carry a dotted field path and a line/column.
- A YAML layer that blocks the two Python-specific conversions that would
  corrupt real files: YAML 1.1 bools (the Norway problem) and implicit
  timestamps.
- Non-destructive writing: every write rotates the previous file to
  `<stem>.<n><ext>`, stages content in a temp file, and never prunes backups.
  `restore_backup` undoes a write, rotating the current file in its turn.
- Comment- and order-preserving edits via `with_updates`; canonical re-emit via
  `with_front_matter`.
- Validation with messages identical to SwiftProyecto's `ProjectValidator`.
  Checks beyond the reference are reported separately in `extra_warnings`.
- Variant resolution, PROJECT.md discovery, episode path templates, and typed
  app-specific settings sections.
- Preservation of unknown keys at the top level and inside seasons, languages,
  variants, and `tts` blocks.

### Known divergences from SwiftProyecto

Documented as D1–D10 in [REQUIREMENTS.md](REQUIREMENTS.md). In short: the port
follows the Swift source rather than its stale documentation, preserves nested
keys that Swift drops, and accepts two real-world shapes Swift mishandles
(`languages: [es, fr]` and `episodes:` without `season:`), reporting each as a
conformance warning.
