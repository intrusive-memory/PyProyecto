"""Front-matter splitting and the parsed document type."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .errors import ConformanceWarning, NoFrontMatterError
from .models import CANONICAL_KEY_ORDER, ProjectFrontMatter
from .yamlcompat import dump_front_matter, load_front_matter

_DELIMITER = "---"


def _split(text: str, path: Path | None) -> tuple[str, str, int]:
    """Return ``(front_matter_text, body, opening_delimiter_line)``.

    Matches Swift: the first line that trims to ``---`` opens the block and the
    next one closes it. The opening delimiter is not required to be line 1
    (open question 5); the validator warns when it is not.
    """
    lines = text.split("\n")
    first: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == _DELIMITER:
            first = index
            break
    if first is None:
        raise NoFrontMatterError(path=path)

    second: int | None = None
    for index in range(first + 1, len(lines)):
        if lines[index].strip() == _DELIMITER:
            second = index
            break
    if second is None:
        raise NoFrontMatterError(path=path)

    front = "\n".join(lines[first + 1 : second])
    body = "\n".join(lines[second + 1 :]).strip()
    return front, body, first


@dataclass(frozen=True, slots=True)
class ProjectDocument:
    """A parsed PROJECT.md: typed front matter, body, and the YAML behind it.

    The loaded YAML mapping is the source of truth. :attr:`front_matter` is
    derived from it, so an edit applied through :meth:`with_updates` cannot
    drift out of sync with what will be written back -- and comments, key
    order, and quoting survive the round trip.
    """

    front_matter: ProjectFrontMatter
    body: str
    raw_text: str
    raw_front_matter: str
    warnings: tuple[ConformanceWarning, ...] = ()
    path: Path | None = None
    leading_text: str = ""
    _data: Mapping[str, Any] = field(default_factory=dict, repr=False)
    _modified: bool = field(default=False, repr=False)

    # -- construction -----------------------------------------------------

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
        *,
        body: str = "",
        path: Path | None = None,
        raw_text: str | None = None,
        raw_front_matter: str | None = None,
        warnings: tuple[ConformanceWarning, ...] = (),
        leading_text: str = "",
        modified: bool = False,
    ) -> ProjectDocument:
        collected: list[ConformanceWarning] = list(warnings)
        front_matter = ProjectFrontMatter.parse(data, collected)
        front_yaml = (
            raw_front_matter
            if raw_front_matter is not None
            else dump_front_matter(data)
        )
        text = (
            raw_text
            if raw_text is not None
            else _render(front_yaml, body, leading_text)
        )
        return cls(
            front_matter=front_matter,
            body=body,
            raw_text=text,
            raw_front_matter=front_yaml,
            warnings=tuple(collected),
            path=path,
            leading_text=leading_text,
            _data=data,
            _modified=modified,
        )

    @classmethod
    def new(cls, front_matter: ProjectFrontMatter, body: str = "") -> ProjectDocument:
        """Build a document from scratch, in canonical key order."""
        return cls.from_mapping(
            _ordered(front_matter.to_yaml()), body=body, modified=True
        )

    # -- editing ----------------------------------------------------------

    def with_updates(self, updates: Mapping[str, Any]) -> ProjectDocument:
        """Apply top-level key updates, preserving everything else verbatim.

        A value of ``None`` removes the key. Existing keys keep their position
        and new keys are appended: reordering an existing document detaches
        comments from the keys they document, and ruamel then re-emits a
        commented block in a form it cannot read back.
        """
        data = _clone(self._data)
        for key, value in updates.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = _matching_style(data.get(key), value)
        return self.from_mapping(
            data,
            body=self.body,
            path=self.path,
            leading_text=self.leading_text,
            modified=True,
        )

    def with_front_matter(self, front_matter: ProjectFrontMatter) -> ProjectDocument:
        """Replace the front matter wholesale, re-emitting in canonical order.

        This discards comments and original key order. Prefer
        :meth:`with_updates` for edits to a file someone maintains by hand.
        """
        return self.from_mapping(
            _ordered(front_matter.to_yaml()),
            body=self.body,
            path=self.path,
            leading_text=self.leading_text,
            modified=True,
        )

    def with_body(self, body: str) -> ProjectDocument:
        return self.from_mapping(
            _clone(self._data),
            body=body.strip(),
            path=self.path,
            raw_front_matter=self.raw_front_matter,
            leading_text=self.leading_text,
            modified=True,
        )

    # -- output -----------------------------------------------------------

    @property
    def is_modified(self) -> bool:
        return self._modified

    @property
    def data(self) -> Mapping[str, Any]:
        """The loaded YAML mapping, including every unknown key."""
        return self._data

    def to_text(self) -> str:
        """Render the document.

        An unmodified document renders as the bytes it was parsed from, so
        reading and writing without edits changes nothing.
        """
        if not self._modified:
            return self.raw_text
        return _render(dump_front_matter(self._data), self.body, self.leading_text)


def _matching_style(old: Any, new: Any) -> Any:
    """Give ``new`` the flow/block style the value it replaces was written in.

    ``tags: [podcast, AI]`` should stay on one line when a caller hands us a
    plain Python list, rather than turning into a block list and making a noisy
    diff in a file someone maintains by hand.
    """
    old_style = getattr(getattr(old, "fa", None), "flow_style", lambda: None)()
    if old_style is None:
        return new
    if isinstance(new, (list, tuple)) and not isinstance(new, str):
        converted: Any = CommentedSeq(new)
    elif isinstance(new, Mapping):
        converted = CommentedMap(new)
    else:
        return new
    converted.fa.set_flow_style() if old_style else converted.fa.set_block_style()
    return converted


def _clone(data: Mapping[str, Any]) -> Any:
    """Copy a loaded structure by round-tripping it through YAML text.

    ``copy.deepcopy`` looks like the obvious way to do this and is wrong:
    ruamel's deep copy detaches comments from the keys they belong to, and the
    re-emitted block ("cast:   -") no longer parses. Serializing and reloading
    is slower and correct.
    """
    return load_front_matter(dump_front_matter(data))


def _render(front_yaml: str, body: str, leading_text: str = "") -> str:
    if not front_yaml.endswith("\n"):
        front_yaml += "\n"
    text = f"{leading_text}{_DELIMITER}\n{front_yaml}{_DELIMITER}\n"
    if body:
        text += f"\n{body}\n"
    return text


def _ordered(data: Mapping[str, Any]) -> Any:
    """Sort known keys into canonical order, keeping unknown keys after them.

    Round-trip containers are reordered in place so comments stay attached to
    their keys.
    """
    known = [k for k in CANONICAL_KEY_ORDER if k in data]
    unknown = [k for k in data if k not in CANONICAL_KEY_ORDER]
    desired = known + unknown
    if list(data.keys()) == desired:
        return data
    try:
        for key in desired:
            value = data.pop(key)  # type: ignore[attr-defined]
            data[key] = value  # type: ignore[index]
        return data
    except (AttributeError, TypeError):  # pragma: no cover - plain dict path
        return {key: data[key] for key in desired}


def parse(text: str, *, path: str | os.PathLike[str] | None = None) -> ProjectDocument:
    """Parse PROJECT.md text."""
    source = Path(path) if path is not None else None
    front, body, first_line = _split(text, source)
    data = load_front_matter(front, path=source)
    if data is None:
        data = {}
    leading = "" if first_line == 0 else "\n".join(text.split("\n")[:first_line]) + "\n"
    return ProjectDocument.from_mapping(
        data,
        body=body,
        path=source,
        raw_text=text,
        raw_front_matter=front,
        leading_text=leading,
    )


def parse_file(path: str | os.PathLike[str]) -> ProjectDocument:
    """Parse a PROJECT.md file from disk (UTF-8, BOM tolerated)."""
    source = Path(path).expanduser()
    text = source.read_text(encoding="utf-8-sig")
    return parse(text, path=source)
