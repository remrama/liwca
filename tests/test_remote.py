"""Tests that fetch every registered remote dictionary.

These tests require network access and are only run on push to main
(not on pull requests). See .github/workflows/tests.yaml.
"""

from __future__ import annotations

import pandas as pd
import pytest

import liwca

_FETCH_FUNCTIONS = [
    ("bigtwo", liwca.fetch_bigtwo),
    ("honor", liwca.fetch_honor),
    ("mystical", liwca.fetch_mystical),
    ("sleep", liwca.fetch_sleep),
    ("threat", liwca.fetch_threat),
]

_EXAMPLES: dict[str, list[str]] = {
    "sleep": ["cant sleep", "couldnt sleep", "didnt sleep"],
    "threat": ["accidents", "accusations", "afraid", "aftermath"],
}


@pytest.mark.parametrize("name,fetch_fn", _FETCH_FUNCTIONS)
def test_fetch_and_validate(name: str, fetch_fn) -> None:
    """Fetch a remote dictionary, verify it loads as a valid DataFrame."""
    dx = fetch_fn()
    assert isinstance(dx, pd.DataFrame)
    assert dx.index.name == "DicTerm"
    assert dx.columns.name == "Category"
    assert len(dx) > 0
    assert dx.shape[1] > 0
    assert set(dx.values.flat) <= {0, 1}


@pytest.mark.parametrize("name,examples", _EXAMPLES.items())
def test_example_terms_in_dictionary(name: str, examples: list[str]) -> None:
    """Verify that known example terms actually exist in the fetched dictionary."""
    fetch_fn = getattr(liwca, f"fetch_{name}")
    dx = fetch_fn()
    missing = [term for term in examples if term not in dx.index]
    assert not missing, f"Example terms not found in '{name}': {missing}"
