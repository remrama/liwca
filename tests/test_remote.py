"""Tests that fetch every registered remote dictionary.

These tests require network access and are only run on push to main
(not on pull requests). See .github/workflows/tests.yaml.
"""

from __future__ import annotations

import pandas as pd
import pytest

import liwca


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
