"""The YAML compatibility layer.

This module exists because Python YAML loaders type values that Swift leaves
alone. SwiftProyecto parses YAML into JSON and then decodes with ``Codable``,
so every scalar reaches its model as a string, a number, or a bool -- never as
a date, and never with YAML 1.1's extended bool vocabulary.

Two differences would silently corrupt real project files:

1. **The Norway problem.** Under YAML 1.1 (PyYAML's default), ``no`` loads as
   ``False``. ``languages: [es, no]`` would become ``['es', False]`` and the
   Norwegian language code would vanish. ruamel defaults to YAML 1.2, where
   only ``true``/``false`` are bools, so this is handled by choosing ruamel --
   but :func:`load_front_matter` asserts it rather than trusting it.

2. **Implicit timestamps.** ruamel resolves ``created: 2025-01-25T00:00:00Z``
   into a ``TimeStamp`` and ``2025-01-15`` into a ``date``. Swift does neither.
   We strip the timestamp constructor so both arrive as strings and a single
   rule in ``models`` decides what a valid date is -- which is also what lets
   us reject date-only values (REQUIREMENTS.md open question 6).

Floats and ints keep YAML semantics: ``model: 1.7b`` is a string, but
``model: 0.6`` is a float, and the models reject it the way Swift's decoder
would.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.error import MarkedYAMLError
from ruamel.yaml.resolver import VersionedResolver

from .errors import InvalidYAMLError

_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"


class _ProyectoConstructor(RoundTripConstructor):
    """Round-trip constructor that leaves timestamp-shaped scalars as text."""


def _construct_timestamp_as_string(constructor: RoundTripConstructor, node: Any) -> str:
    return str(node.value)


_ProyectoConstructor.add_constructor(_TIMESTAMP_TAG, _construct_timestamp_as_string)


class _NoTimestampResolver(VersionedResolver):
    """Resolver with the implicit ``timestamp`` rule removed.

    On load this keeps date-shaped scalars as strings. On dump it is what lets
    ``created: 2025-01-25T00:00:00Z`` be emitted unquoted, the way Swift writes
    it -- otherwise the emitter quotes it to stop a reader from resolving it
    back into a timestamp.
    """

    @property
    def versioned_resolver(self) -> Any:
        resolvers = super().versioned_resolver
        return {
            char: [
                (tag, regexp)
                for tag, regexp in entries
                if not tag.endswith(":timestamp")
            ]
            for char, entries in resolvers.items()
        }


def make_yaml() -> YAML:
    """Build the one YAML configuration PyProyecto reads and writes with.

    Round-trip mode is deliberate: it preserves comments, key order, and
    quoting style, which is what makes non-destructive writes possible (see
    :mod:`pyproyecto.writer`).
    """
    yaml = YAML(typ="rt")
    # Belt and braces: the resolver stops timestamp-shaped scalars from being
    # tagged, and the constructor is what would handle any that still were.
    yaml.Resolver = _NoTimestampResolver
    yaml.Constructor = _ProyectoConstructor
    yaml.preserve_quotes = True
    # Match the hand-rolled Swift emitter: two-space indent, sequences indented
    # under their key with the dash at the parent's indentation + 2.
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # Never fold long description lines.
    return yaml


def load_front_matter(text: str, *, path: Path | None = None) -> Any:
    """Load front-matter YAML text into a round-trippable structure."""
    yaml = make_yaml()
    try:
        return yaml.load(text)
    except MarkedYAMLError as exc:
        mark = exc.problem_mark
        raise InvalidYAMLError(
            exc.problem or str(exc),
            path=path,
            line=None if mark is None else mark.line + 1,
            column=None if mark is None else mark.column + 1,
        ) from exc
    except Exception as exc:  # pragma: no cover - ruamel raises many shapes
        raise InvalidYAMLError(str(exc), path=path) from exc


def dump_front_matter(data: Any) -> str:
    """Serialize a loaded structure back to YAML text."""
    yaml = make_yaml()
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    return buffer.getvalue()
