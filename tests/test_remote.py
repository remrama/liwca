"""Tests that fetch every registered remote dataset.

These tests require network access and are only run on push to main
(not on pull requests). See .github/workflows/tests.yaml.
"""

from __future__ import annotations

import pandas as pd
import pytest

from liwca.datasets import corpora, dictionaries, tables

# ---------------------------------------------------------------------------
# Dictionaries
# ---------------------------------------------------------------------------

_DICTIONARY_FETCHERS = [
    ("bigtwo", dictionaries.fetch_bigtwo),
    ("emfd", dictionaries.fetch_emfd),
    ("honor", dictionaries.fetch_honor),
    ("leeq", dictionaries.fetch_leeq),
    ("mystical", dictionaries.fetch_mystical),
    ("sleep", dictionaries.fetch_sleep),
    ("threat", dictionaries.fetch_threat),
    ("wrad", dictionaries.fetch_wrad),
]

_DICTIONARY_EXAMPLES: dict[str, list[str]] = {
    "sleep": ["cant sleep", "couldnt sleep", "didnt sleep"],
    "threat": ["accidents", "accusations", "afraid", "aftermath"],
}


@pytest.mark.parametrize("name,fetch_fn", _DICTIONARY_FETCHERS)
def test_fetch_dictionary(name: str, fetch_fn) -> None:
    """Fetch a remote dictionary, verify it loads as a valid dictionary DataFrame."""
    dx = fetch_fn()
    assert isinstance(dx, pd.DataFrame)
    assert dx.index.name == "DicTerm"
    assert dx.columns.name == "Category"
    assert len(dx) > 0
    assert dx.shape[1] > 0
    assert set(dx.values.flat) <= {0, 1}


@pytest.mark.parametrize("name,examples", _DICTIONARY_EXAMPLES.items())
def test_example_terms_in_dictionary(name: str, examples: list[str]) -> None:
    """Verify that known example terms actually exist in the fetched dictionary."""
    fetch_fn = getattr(dictionaries, f"fetch_{name}")
    dx = fetch_fn()
    missing = [term for term in examples if term not in dx.index]
    assert not missing, f"Example terms not found in '{name}': {missing}"


# ---------------------------------------------------------------------------
# Corpora
# ---------------------------------------------------------------------------

_CORPUS_FETCHERS = [
    ("autobiomemsim", corpora.fetch_autobiomemsim),
    ("cmu_books", corpora.fetch_cmu_books),
    ("cmu_movies", corpora.fetch_cmu_movies),
    ("hippocorpus", corpora.fetch_hippocorpus),
    ("liwc_demo_data", corpora.fetch_liwc_demo_data),
    ("sherlock", corpora.fetch_sherlock),
    ("rwritingprompts", corpora.fetch_rwritingprompts),
]


@pytest.mark.parametrize("name,fetch_fn", _CORPUS_FETCHERS)
def test_fetch_corpus(name: str, fetch_fn) -> None:
    """Fetch a remote corpus, verify it loads as a non-empty DataFrame."""
    df = fetch_fn()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

_TABLE_FETCHERS = [
    ("liwc2015norms", tables.fetch_liwc2015norms),
    ("liwc22norms", tables.fetch_liwc22norms),
    ("psychnorms", tables.fetch_psychnorms),
    ("scope", tables.fetch_scope),
]


@pytest.mark.parametrize("name,fetch_fn", _TABLE_FETCHERS)
def test_fetch_table(name: str, fetch_fn) -> None:
    """Fetch a remote table, verify it loads as a non-empty DataFrame."""
    df = fetch_fn()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
