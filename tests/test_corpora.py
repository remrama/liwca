"""Tests for liwca.datasets.corpora - fetch functions and registry integrity."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from liwca.datasets import corpora

# ---------------------------------------------------------------------------
# Fetch function API
# ---------------------------------------------------------------------------

_FETCH_FUNCTIONS = [
    corpora.fetch_autobiomemsim,
    corpora.fetch_cmu_books,
    corpora.fetch_cmu_movies,
    corpora.fetch_hippocorpus,
    corpora.fetch_liwc_demo_data,
    corpora.fetch_sherlock,
    corpora.fetch_rwritingprompts,
]

# Filenames each public fetcher pulls from the shared Pooch registry.
# Used by the registry-subset test below to catch typos like a fetch_*
# function calling _pup.fetch("foo-bar.txt") when the registry key is
# "foo_bar.txt".
_EXPECTED_REGISTRY_KEYS: dict[str, set[str]] = {
    "fetch_autobiomemsim": {"autobiomemsem.zip"},
    "fetch_cmu_books": {"booksummaries.tar.gz"},
    "fetch_cmu_movies": {"MovieSummaries.tar.gz"},
    "fetch_hippocorpus": {"hippocorpus.zip"},
    "fetch_liwc_demo_data": {"liwc22-demo-data.zip"},
    "fetch_sherlock": {"sherlock.zip"},
    "fetch_rwritingprompts": {"reddit_short_stories.txt"},
}


class TestFetchFunctions:
    """Basic API checks for all fetch functions (no network required)."""

    @pytest.mark.parametrize("fetch_fn", _FETCH_FUNCTIONS)
    def test_callable(self, fetch_fn) -> None:
        assert callable(fetch_fn)

    def test_download_failure_raises(self) -> None:
        """Pooch errors propagate up from fetch functions."""
        with patch.object(corpora._pup, "fetch", side_effect=ConnectionError("no internet")):
            with pytest.raises(ConnectionError):
                corpora.fetch_cmu_books()


# ---------------------------------------------------------------------------
# Registry integrity
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    """Tests validating that corpus fetchers reference real registry keys."""

    def test_corpora_filenames_registered(self) -> None:
        """Every filename a public corpus fetcher requests is registered."""
        expected = set().union(*_EXPECTED_REGISTRY_KEYS.values())
        registry = set(corpora._pup.registry.keys())
        missing = expected - registry
        assert not missing, f"Corpus filenames missing from registry: {sorted(missing)}"
