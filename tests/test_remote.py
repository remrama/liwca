"""Tests that fetch every registered remote dictionary.

These tests require network access and are only run on push to main
(not on pull requests). See .github/workflows/tests.yaml.
"""

from __future__ import annotations

import pandas as pd
import pytest

import liwca
from liwca._catalogue import CATALOGUE


@pytest.mark.parametrize("dic_name", liwca.list_available())
def test_fetch_and_validate(dic_name: str) -> None:
    """Fetch a remote dictionary, verify it loads as a valid DataFrame."""
    dx = liwca.fetch_dx(dic_name)
    assert isinstance(dx, pd.DataFrame)
    assert dx.index.name == "DicTerm"
    assert dx.columns.name == "Category"
    assert len(dx) > 0
    assert dx.shape[1] > 0
    assert set(dx.values.flat) <= {0, 1}


@pytest.mark.parametrize(
    "dic_name",
    [name for name, info in CATALOGUE.items() if info.examples],
)
def test_example_terms_in_dictionary(dic_name: str) -> None:
    """Verify that catalogue example terms actually exist in the fetched dictionary."""
    dx = liwca.fetch_dx(dic_name)
    info = CATALOGUE[dic_name]
    missing = [term for term in info.examples if term not in dx.index]
    assert not missing, f"Example terms not found in '{dic_name}': {missing}"
