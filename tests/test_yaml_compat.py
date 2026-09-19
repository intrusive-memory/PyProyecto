"""The platform differences between Swift's YAML handling and Python's.

These are the tests that stop a Python YAML loader from quietly changing
project data that SwiftProyecto would have left alone.
"""

from __future__ import annotations

import pytest

from pyproyecto import InvalidYAMLError, parse, parse_file
from pyproyecto.yamlcompat import load_front_matter


def test_norway_problem_language_codes_stay_strings(adversarial):
    """`no` is Norwegian, not False. YAML 1.1 loaders get this wrong."""
    doc = parse_file(adversarial / "norway.md")
    codes = [lang.code for lang in doc.front_matter.languages]
    assert codes == ["es", "no", "on", "off", "yes"]
    assert all(isinstance(code, str) for code in codes)


def test_bare_yes_no_scalars_stay_strings():
    data = load_front_matter("a: no\nb: yes\nc: on\nd: off\ne: y\nf: n\n")
    assert list(data.values()) == ["no", "yes", "on", "off", "y", "n"]


def test_real_booleans_are_still_booleans():
    data = load_front_matter("a: true\nb: false\n")
    assert data["a"] is True
    assert data["b"] is False


def test_timestamps_are_not_auto_converted():
    """Swift gets a string here; so must we, or date rules would differ."""
    data = load_front_matter("created: 2025-01-25T00:00:00Z\nday: 2025-01-15\n")
    assert data["created"] == "2025-01-25T00:00:00Z"
    assert data["day"] == "2025-01-15"
    assert isinstance(data["created"], str)
    assert isinstance(data["day"], str)


def test_unquoted_version_like_string_is_a_string(minimal):
    doc = parse(minimal.replace("---\n", "---\ntts:\n  model: 1.7b\n", 1))
    assert doc.front_matter.tts.model == "1.7b"


def test_unquoted_numeric_model_is_rejected_like_swift(adversarial):
    """`model: 0.6` is a float in YAML; Swift's decoder rejects it."""
    with pytest.raises(InvalidYAMLError) as excinfo:
        parse_file(adversarial / "numeric-model.md")
    assert "tts.model" in str(excinfo.value)


def test_yaml_error_reports_position():
    with pytest.raises(InvalidYAMLError) as excinfo:
        parse("---\ntype: project\n  bad indent: x\n---\n")
    assert excinfo.value.line is not None


def test_duplicate_keys_are_rejected():
    with pytest.raises(InvalidYAMLError):
        parse("---\ntype: project\ntype: overview\n---\n")
