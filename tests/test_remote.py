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

_BINARY_DICTIONARY_FETCHERS = [
    ("bigtwo", dictionaries.fetch_bigtwo),
    ("emfd", dictionaries.fetch_emfd),
    ("empath", dictionaries.fetch_empath),
    ("honor", dictionaries.fetch_honor),
    ("leeq", dictionaries.fetch_leeq),
    ("mystical", dictionaries.fetch_mystical),
    ("sleep", dictionaries.fetch_sleep),
    ("threat", dictionaries.fetch_threat),
]

_WEIGHTED_DICTIONARY_FETCHERS = [
    ("wrad", dictionaries.fetch_wrad),
]

_DICTIONARY_EXAMPLES: dict[str, list[str]] = {
    "sleep": ["cant sleep", "couldnt sleep", "didnt sleep"],
    "threat": ["accidents", "accusations", "afraid", "aftermath"],
}


@pytest.mark.parametrize("name,fetch_fn", _BINARY_DICTIONARY_FETCHERS)
def test_fetch_binary_dictionary(name: str, fetch_fn) -> None:
    """Fetch a remote binary dictionary; verify int8 0/1 dtype and shape."""
    dx = fetch_fn()
    assert isinstance(dx, pd.DataFrame)
    assert dx.index.name == "DicTerm"
    assert dx.columns.name == "Category"
    assert len(dx) > 0
    assert dx.shape[1] > 0
    assert set(dx.values.flat) <= {0, 1}
    assert dx.dtypes.eq("int8").all()


@pytest.mark.parametrize("name,fetch_fn", _WEIGHTED_DICTIONARY_FETCHERS)
def test_fetch_weighted_dictionary(name: str, fetch_fn) -> None:
    """Fetch a remote weighted dictionary; verify float64 dtype and shape."""
    dx = fetch_fn()
    assert isinstance(dx, pd.DataFrame)
    assert dx.index.name == "DicTerm"
    assert dx.columns.name == "Category"
    assert len(dx) > 0
    assert dx.shape[1] > 0
    assert dx.dtypes.eq("float64").all()


@pytest.mark.parametrize("name,examples", _DICTIONARY_EXAMPLES.items())
def test_example_terms_in_dictionary(name: str, examples: list[str]) -> None:
    """Verify that known example terms actually exist in the fetched dictionary."""
    fetch_fn = getattr(dictionaries, f"fetch_{name}")
    dx = fetch_fn()
    missing = [term for term in examples if term not in dx.index]
    assert not missing, f"Example terms not found in '{name}': {missing}"


# ---------------------------------------------------------------------------
# Metabase per-stem fetchers (SCOPE / psychNorms)
# ---------------------------------------------------------------------------

# (source, stem) representative pairs; one pair each is enough to exercise
# the lazy-build, lowercase-normalisation, and weighted-.dicx round-trip.
_METABASE_STEM_FETCHERS = [
    ("scope", "Conc_Brys"),  # PascalCase input - exercises lowercase normalisation
    ("psychnorms", "concreteness_brysbaert"),
]


@pytest.mark.parametrize("source,stem", _METABASE_STEM_FETCHERS)
def test_fetch_metabase_stem(source: str, stem: str) -> None:
    """Slice one column from a metabase; verify weighted-dicx shape and dtype."""
    fetch_fn = getattr(dictionaries, f"fetch_{source}")
    dx = fetch_fn(stem)
    assert isinstance(dx, pd.DataFrame)
    assert dx.index.name == "DicTerm"
    assert dx.columns.name == "Category"
    assert dx.shape[0] > 0
    assert dx.shape[1] == 1
    assert dx.dtypes.eq("float64").all()


def test_list_metabase_stems_nonempty() -> None:
    """Stem listings are populated from the upstream metadata files."""
    scope_stems = dictionaries.list_scope_stems()
    pn_stems = dictionaries.list_psychnorms_stems()
    assert len(scope_stems) > 100
    assert len(pn_stems) > 100
    # Behavioural Response Variables and POS columns are excluded.
    assert "lexicald_rt_v_elp" not in scope_stems  # SCOPE Response Variable
    assert "pos_brysbaert" not in pn_stems  # psychNorms part_of_speech


# ---------------------------------------------------------------------------
# Corpora
# ---------------------------------------------------------------------------

_CORPUS_FETCHERS = [
    ("autobiomemsim", corpora.fetch_autobiomemsim),
    ("cmu_book_summaries", corpora.fetch_cmu_book_summaries),
    ("cmu_movie_summaries", corpora.fetch_cmu_movie_summaries),
    ("hippocorpus", corpora.fetch_hippocorpus),
    ("liwc22_demo_data", corpora.fetch_liwc22_demo_data),
    ("reddit_short_stories", corpora.fetch_reddit_short_stories),
    ("sherlock", corpora.fetch_sherlock),
    ("tedtalks", corpora.fetch_tedtalks),
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
