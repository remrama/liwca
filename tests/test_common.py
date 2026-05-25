"""Tests for liwca.datasets._common shared helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from liwca.datasets import corpora, dictionaries, tables

_GET_LOCATION_CASES = [
    ("corpora", corpora.get_location),
    ("dictionaries", dictionaries.get_location),
    ("tables", tables.get_location),
]


@pytest.mark.parametrize("category,get_location", _GET_LOCATION_CASES)
def test_get_location(category: str, get_location) -> None:
    """Per-module get_location() returns a Path ending in the category name."""
    loc = get_location()
    assert isinstance(loc, Path)
    assert loc.name == category
